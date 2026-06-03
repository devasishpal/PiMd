"""Pipeline engine — composable conversion stages with lifecycle hooks."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageType(str, Enum):
    """Built-in pipeline stage types."""

    PARSE = "parse"
    TRANSFORM = "transform"
    RENDER = "render"
    POST_PROCESS = "post_process"
    EXPORT = "export"
    CUSTOM = "custom"


@dataclass
class PipelineContext:
    """Shared context passed through pipeline stages."""

    source_path: str | None = None
    source_text: str | None = None
    document: Any = None
    output_path: str | None = None
    output_bytes: bytes | None = None
    options: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_error(self, stage: str, exc: Exception) -> None:
        self.errors.append({"stage": stage, "error": str(exc), "type": type(exc).__name__})


class PipelineStage(ABC):
    """Base class for a single pipeline stage."""

    def __init__(self, name: str, stage_type: StageType = StageType.CUSTOM) -> None:
        self.name = name
        self.stage_type = stage_type

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> PipelineContext:
        """Execute this stage. Return the (possibly modified) context."""

    def __repr__(self) -> str:
        return f"<PipelineStage '{self.name}' ({self.stage_type.value})>"


@dataclass
class StageResult:
    """Result of a single pipeline stage execution."""

    stage_name: str
    duration: float
    success: bool
    error: str | None = None


class Pipeline:
    """An ordered sequence of stages forming a conversion pipeline."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> Pipeline:
        self._stages.append(stage)
        return self

    def insert_stage(self, index: int, stage: PipelineStage) -> Pipeline:
        self._stages.insert(index, stage)
        return self

    def remove_stage(self, name: str) -> Pipeline:
        self._stages = [s for s in self._stages if s.name != name]
        return self

    def get_stage(self, name: str) -> PipelineStage | None:
        for s in self._stages:
            if s.name == name:
                return s
        return None

    def list_stages(self) -> list[PipelineStage]:
        return list(self._stages)

    def run(self, ctx: PipelineContext) -> tuple[PipelineContext, list[StageResult]]:
        """Execute all stages in order. Collects timing and errors."""
        results: list[StageResult] = []
        for stage in self._stages:
            t0 = time.perf_counter()
            success = True
            error: str | None = None
            try:
                ctx = stage.execute(ctx)
            except Exception as exc:
                success = False
                error = str(exc)
                ctx.add_error(stage.name, exc)
            duration = time.perf_counter() - t0
            results.append(
                StageResult(
                    stage_name=stage.name,
                    duration=duration,
                    success=success,
                    error=error,
                )
            )
            if not success and not ctx.options.get("continue_on_error", True):
                break
        return ctx, results


class PipelineManager:
    """Manage named pipelines and provide default conversion pipelines."""

    def __init__(self) -> None:
        self._pipelines: dict[str, Pipeline] = {}

    def register(self, name: str, pipeline: Pipeline) -> None:
        self._pipelines[name] = pipeline

    def get(self, name: str) -> Pipeline | None:
        return self._pipelines.get(name)

    def list_pipelines(self) -> list[str]:
        return list(self._pipelines.keys())

    @staticmethod
    def default_md_pipeline() -> Pipeline:
        from pimd.converters.markdown import MarkdownConverter

        p = Pipeline("markdown")
        p.add_stage(ParseStage("parse_md", MarkdownConverter()))
        p.add_stage(RenderStage("render_docx"))
        return p

    @staticmethod
    def default_html_pipeline() -> Pipeline:
        from pimd.converters.html import HTMLConverter

        p = Pipeline("html")
        p.add_stage(ParseStage("parse_html", HTMLConverter()))
        p.add_stage(RenderStage("render_docx"))
        return p


# === Built-in stages ===


class ParseStage(PipelineStage):
    """Parse source text into a Document model."""

    def __init__(self, name: str = "parse", converter: Any = None) -> None:
        super().__init__(name, StageType.PARSE)
        self._converter = converter

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.source_text is None and ctx.source_path:
            with open(ctx.source_path, encoding="utf-8", errors="replace") as f:
                ctx.source_text = f.read()
        if ctx.source_text is None:
            raise ValueError("No source text or path provided")
        if self._converter is not None:
            doc = self._converter.parse_text(ctx.source_text)
        else:
            from pimd.parsers.markdown import MarkdownParser

            doc = MarkdownParser().parse(ctx.source_text)
        ctx.document = doc
        ctx.options.setdefault("continue_on_error", True)
        return ctx


class TransformStage(PipelineStage):
    """Transform a document (diagrams, equations, etc.)."""

    def __init__(self, name: str = "transform", transforms: list[Any] | None = None) -> None:
        super().__init__(name, StageType.TRANSFORM)
        self._transforms = transforms or []

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        for transform in self._transforms:
            try:
                ctx.document = transform(ctx.document)
            except Exception as exc:
                tname = getattr(transform, "__name__", str(transform))
                ctx.add_warning(
                    f"Transform '{tname}' failed: {exc}"
                )
        return ctx


class RenderStage(PipelineStage):
    """Render a Document model to output format."""

    def __init__(
        self,
        name: str = "render",
        renderer: Any = None,
        output_format: str = "docx",
    ) -> None:
        super().__init__(name, StageType.RENDER)
        self._renderer = renderer
        self._output_format = output_format

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if self._renderer is not None:
            renderer = self._renderer
        elif self._output_format == "docx":
            from pimd.renderers.docx_renderer import DocxRenderer

            renderer = DocxRenderer()
        elif self._output_format == "html":
            from pimd.renderers.html_renderer import HtmlRenderer

            renderer = HtmlRenderer()
        else:
            raise ValueError(f"Unknown output format: {self._output_format}")

        if ctx.output_path:
            renderer.render(ctx.document, ctx.output_path, **ctx.options)
        else:
            ctx.output_bytes = renderer.render_to_bytes(ctx.document, **ctx.options)
        return ctx


class ExportStage(PipelineStage):
    """Export rendered output to a different format."""

    def __init__(self, name: str = "export", target_format: str = "pdf") -> None:
        super().__init__(name, StageType.EXPORT)
        self._target_format = target_format

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.output_path:
            from pimd.export.converter import ExportConverter

            result = ExportConverter().convert(
                ctx.output_path,
                self._target_format,
            )
            if result.success and result.output_path:
                ctx.output_path = str(result.output_path)
        return ctx


class PostProcessStage(PipelineStage):
    """Post-process the output (watermarks, covers, branding)."""

    def __init__(self, name: str = "post_process", processors: list[Any] | None = None) -> None:
        super().__init__(name, StageType.POST_PROCESS)
        self._processors = processors or []

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        for processor in self._processors:
            try:
                processor(ctx)
            except Exception as exc:
                pname = getattr(processor, "__name__", str(processor))
                ctx.add_warning(
                    f"Post-processor '{pname}' failed: {exc}"
                )
        return ctx
