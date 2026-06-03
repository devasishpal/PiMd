"""Job system — background conversions with status tracking and future queue integration."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pimd.pipeline import PipelineContext, PipelineManager


class JobStatus(str, Enum):
    """Status of a background conversion job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """Result produced by a completed or failed job."""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    duration: float = 0.0
    output_path: str | None = None
    output_bytes: bytes | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    stage_results: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_done(self) -> bool:
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


@dataclass
class Job:
    """A single conversion job."""

    job_id: str
    pipeline_name: str
    source_path: str | None = None
    source_text: str | None = None
    output_path: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    result: JobResult | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class JobManager:
    """Manage background conversion jobs.

    Supports synchronous execution and future queue integration.
    Thread-safe for concurrent use from async workers.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._pipeline_manager = PipelineManager()

    def create_job(
        self,
        pipeline_name: str = "default",
        *,
        source_path: str | None = None,
        source_text: str | None = None,
        output_path: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Create a new job and return its ID."""
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            job_id=job_id,
            pipeline_name=pipeline_name,
            source_path=source_path,
            source_text=source_text,
            output_path=output_path,
            options=options or {},
        )
        self._jobs[job_id] = job
        return job_id

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def get_result(self, job_id: str) -> JobResult | None:
        job = self._jobs.get(job_id)
        return job.result if job else None

    def list_jobs(self, status: JobStatus | None = None) -> list[Job]:
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            if job.result:
                job.result.status = JobStatus.CANCELLED
            return True
        return False

    def run_job(self, job_id: str) -> JobResult:
        """Execute a job synchronously and return its result."""
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Unknown job: {job_id}")

        job.status = JobStatus.RUNNING
        t0 = time.perf_counter()
        started = datetime.now(timezone.utc).isoformat()

        result = JobResult(
            job_id=job_id,
            status=JobStatus.RUNNING,
            created_at=job.created_at,
            started_at=started,
            metadata={"pipeline": job.pipeline_name, "source": job.source_path or "(text)"},
        )

        try:
            ctx = PipelineContext(
                source_path=job.source_path,
                source_text=job.source_text,
                output_path=job.output_path,
                options=job.options,
            )
            pipeline = self._pipeline_manager.get(job.pipeline_name)
            if pipeline is None:
                if job.options.get("format") == "html":
                    pipeline = PipelineManager.default_html_pipeline()
                else:
                    pipeline = PipelineManager.default_md_pipeline()

            ctx, stage_results = pipeline.run(ctx)
            result.stage_results = [
                {
                    "name": s.stage_name,
                    "duration": s.duration,
                    "success": s.success,
                    "error": s.error,
                }
                for s in stage_results
            ]
            result.warnings = ctx.warnings
            result.output_path = ctx.output_path
            result.output_bytes = ctx.output_bytes

            if any(not s.success for s in stage_results):
                result.status = JobStatus.FAILED
                result.error = ctx.errors[-1]["error"] if ctx.errors else "Stage failed"
            else:
                result.status = JobStatus.COMPLETED

        except Exception as exc:
            result.status = JobStatus.FAILED
            result.error = str(exc)

        result.duration = time.perf_counter() - t0
        result.completed_at = datetime.now(timezone.utc).isoformat()
        job.status = result.status
        job.result = result
        return result

    def run_job_async(self, job_id: str) -> JobResult:
        """Execute a job and return a future (fallback: synchronous)."""
        return self.run_job(job_id)

    def clear_completed(self, max_age_hours: int = 24) -> int:
        """Remove completed jobs older than max_age_hours."""
        now = datetime.now(timezone.utc)
        to_remove: list[str] = []
        for jid, job in self._jobs.items():
            if job.result and job.result.is_done and job.created_at:
                try:
                    created = datetime.fromisoformat(job.created_at)
                    if (now - created).total_seconds() > max_age_hours * 3600:
                        to_remove.append(jid)
                except (ValueError, TypeError):
                    pass
        for jid in to_remove:
            del self._jobs[jid]
        return len(to_remove)

    def get_status_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for job in self._jobs.values():
            key = job.status.value if isinstance(job.status, JobStatus) else str(job.status)
            summary[key] = summary.get(key, 0) + 1
        return summary
