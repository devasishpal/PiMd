"""Extended tests for the PiMD observability module."""

from __future__ import annotations

from pimd.models import DocumentStatistics
from pimd.observability import (
    BuildMetrics,
    ConversionMetrics,
    ConversionReport,
    ExecutionReport,
    MemorySnapshot,
    MetricsCollector,
    PipelineProfile,
    Profiler,
    Timer,
    measure_time,
    profile_conversion,
)


class TestTimer:
    def test_context_manager_records_elapsed(self) -> None:
        with Timer("test") as t:
            pass
        assert t.elapsed >= 0
        assert t.seconds == t.elapsed

    def test_seconds_and_milliseconds(self) -> None:
        t = Timer("test")
        t.elapsed = 1.5
        assert t.seconds == 1.5
        assert t.milliseconds == 1500.0

    def test_lap_records_times(self) -> None:
        t = Timer("multi")
        t.start_timer()
        t.lap("step1")
        t.lap("step2")
        assert len(t.laps) == 2
        assert t.laps[0]["label"] == "step1"
        assert t.laps[1]["label"] == "step2"
        assert t.laps[0]["time"] <= t.laps[1]["time"]

    def test_lap_returns_float(self) -> None:
        t = Timer()
        t.start_timer()
        elapsed = t.lap("only")
        assert isinstance(elapsed, float)
        assert elapsed >= 0

    def test_reset(self) -> None:
        t = Timer("r")
        t.elapsed = 99.0
        t.laps.append({"label": "x", "time": 1.0})
        t.reset()
        assert t.elapsed == 0.0
        assert t.laps == []
        assert t._start == 0.0

    def test_float_conversion(self) -> None:
        t = Timer()
        t.elapsed = 3.14
        assert float(t) == 3.14

    def test_context_manager_name(self) -> None:
        with Timer("my-timer") as t:
            pass
        assert t.name == "my-timer"

    def test_start_timer_sets_start(self) -> None:
        t = Timer()
        t.start_timer()
        assert t._start > 0

    def test_multiple_laps_sequential(self) -> None:
        t = Timer()
        t.start_timer()
        t.lap("a")
        t.lap("b")
        t.lap("c")
        assert len(t.laps) == 3


class TestConversionMetrics:
    def test_defaults(self) -> None:
        m = ConversionMetrics()
        assert m.parse_time == 0.0
        assert m.render_time == 0.0
        assert m.total_time == 0.0
        assert m.input_size == 0
        assert m.output_size == 0
        assert m.block_count == 0

    def test_to_dict(self) -> None:
        m = ConversionMetrics(
            parse_time=0.5,
            render_time=1.2,
            total_time=2.0,
            input_size=1000,
            output_size=500,
            block_count=42,
        )
        d = m.to_dict()
        assert d["parse_time"] == 0.5
        assert d["render_time"] == 1.2
        assert d["total_time"] == 2.0
        assert d["input_size"] == 1000
        assert d["output_size"] == 500
        assert d["block_count"] == 42


class TestConversionReport:
    def test_defaults(self) -> None:
        r = ConversionReport()
        assert r.source_format == ""
        assert r.target_format == "docx"
        assert r.success is True
        assert r.error is None
        assert r.cache_hit is False
        assert r.total_seconds == 0.0

    def test_total_ms(self) -> None:
        r = ConversionReport()
        r.total_seconds = 2.0
        assert r.total_ms == 2000.0

    def test_blocks_per_second(self) -> None:
        r = ConversionReport()
        r.total_seconds = 10.0
        r.blocks_processed = 100
        assert r.blocks_per_second == 10.0

    def test_blocks_per_second_zero_time(self) -> None:
        r = ConversionReport()
        assert r.blocks_per_second == 0.0

    def test_to_dict_contains_all_keys(self) -> None:
        r = ConversionReport(
            source_format="markdown",
            target_format="docx",
            total_seconds=3.5,
            blocks_processed=50,
        )
        d = r.to_dict()
        assert d["source_format"] == "markdown"
        assert d["target_format"] == "docx"
        assert d["total_seconds"] == 3.5
        assert d["blocks_processed"] == 50

    def test_to_dict_with_statistics(self) -> None:
        stats = DocumentStatistics(
            heading_count=3,
            paragraph_count=10,
            word_count=200,
        )
        r = ConversionReport(statistics=stats)
        d = r.to_dict()
        assert d["statistics"]["heading_count"] == 3
        assert d["statistics"]["word_count"] == 200

    def test_to_dict_without_statistics(self) -> None:
        r = ConversionReport()
        d = r.to_dict()
        assert d["statistics"] == {}

    def test_summary_includes_source_format(self) -> None:
        r = ConversionReport(source_format="markdown")
        s = r.summary()
        assert "markdown" in s

    def test_summary_includes_error(self) -> None:
        r = ConversionReport(error="Something broke")
        s = r.summary()
        assert "Something broke" in s

    def test_summary_includes_stages(self) -> None:
        r = ConversionReport(stages={"parse": 0.5, "render": 1.0})
        s = r.summary()
        assert "parse" in s
        assert "render" in s

    def test_summary_includes_timing(self) -> None:
        r = ConversionReport()
        r.metrics.total_time = 5.0
        r.metrics.parse_time = 2.0
        s = r.summary()
        assert "5.00s" in s
        assert "2.00s" in s

    def test_summary_includes_sizes(self) -> None:
        r = ConversionReport()
        r.metrics.input_size = 2048
        r.metrics.output_size = 1024
        s = r.summary()
        assert "2,048" in s
        assert "1,024" in s

    def test_summary_includes_memory(self) -> None:
        r = ConversionReport(memory_delta_mb=15.5, memory_peak_mb=64.0)
        s = r.summary()
        assert "+15.5 MB" in s
        assert "64.0 MB" in s

    def test_summary_includes_blocks(self) -> None:
        r = ConversionReport(blocks_processed=100, total_seconds=10.0)
        s = r.summary()
        assert "100" in s

    def test_summary_includes_diagrams(self) -> None:
        r = ConversionReport(diagrams_rendered=5)
        s = r.summary()
        assert "5" in s
        assert "Diagrams" in s

    def test_summary_includes_equations(self) -> None:
        r = ConversionReport(equations_rendered=3)
        s = r.summary()
        assert "3" in s
        assert "Equations" in s

    def test_summary_includes_error_section(self) -> None:
        r = ConversionReport(error="timeout")
        s = r.summary()
        assert "Error" in s
        assert "timeout" in s


class TestMemorySnapshot:
    def test_take_returns_snapshot(self) -> None:
        snap = MemorySnapshot.take()
        assert isinstance(snap, MemorySnapshot)
        assert snap.gc_objects > 0

    def test_subtract(self) -> None:
        a = MemorySnapshot(rss_mb=100.0, vms_mb=200.0, gc_objects=1000)
        b = MemorySnapshot(rss_mb=80.0, vms_mb=150.0, gc_objects=800)
        diff = a - b
        assert diff.rss_mb == 20.0
        assert diff.vms_mb == 50.0
        assert diff.gc_objects == 200


class TestPipelineProfile:
    def test_fastest_stage(self) -> None:
        pp = PipelineProfile(stage_times={"parse": 0.5, "render": 1.0, "export": 0.3})
        assert pp.fastest_stage() == "export"

    def test_slowest_stage(self) -> None:
        pp = PipelineProfile(stage_times={"parse": 0.5, "render": 1.0, "export": 0.3})
        assert pp.slowest_stage() == "render"

    def test_fastest_stage_empty(self) -> None:
        pp = PipelineProfile()
        assert pp.fastest_stage() is None

    def test_slowest_stage_empty(self) -> None:
        pp = PipelineProfile()
        assert pp.slowest_stage() is None

    def test_total_ms(self) -> None:
        pp = PipelineProfile(total_seconds=2.5)
        assert pp.total_ms == 2500.0


class TestProfiler:
    def test_snapshot(self) -> None:
        profiler = Profiler()
        snap = profiler.snapshot("before")
        assert isinstance(snap, MemorySnapshot)
        assert snap.gc_objects > 0

    def test_timer_creates_and_stores(self) -> None:
        profiler = Profiler()
        t = profiler.timer("mytimer")
        assert isinstance(t, Timer)
        assert t.name == "mytimer"

    def test_get_timer_returns_none_for_unknown(self) -> None:
        profiler = Profiler()
        assert profiler.get_timer("nonexistent") is None

    def test_get_timer_returns_timer(self) -> None:
        profiler = Profiler()
        t = profiler.timer("known")
        assert profiler.get_timer("known") is t

    def test_peak_memory_no_snapshots(self) -> None:
        profiler = Profiler()
        assert profiler.peak_memory_mb() == 0.0

    def test_peak_memory_with_snapshots(self) -> None:
        profiler = Profiler()
        profiler._snapshots = [
            MemorySnapshot(rss_mb=50.0, vms_mb=100.0, gc_objects=500),
            MemorySnapshot(rss_mb=75.0, vms_mb=150.0, gc_objects=600),
            MemorySnapshot(rss_mb=60.0, vms_mb=120.0, gc_objects=550),
        ]
        assert profiler.peak_memory_mb() == 75.0

    def test_first_snapshot(self) -> None:
        profiler = Profiler()
        assert profiler.first_snapshot is None
        profiler._snapshots = [MemorySnapshot(rss_mb=10.0, vms_mb=20.0)]
        assert profiler.first_snapshot is not None
        assert profiler.first_snapshot.rss_mb == 10.0

    def test_last_snapshot(self) -> None:
        profiler = Profiler()
        assert profiler.last_snapshot is None
        profiler._snapshots = [MemorySnapshot(rss_mb=10.0), MemorySnapshot(rss_mb=20.0)]
        assert profiler.last_snapshot is not None
        assert profiler.last_snapshot.rss_mb == 20.0

    def test_report_includes_timers(self) -> None:
        profiler = Profiler()
        t = profiler.timer("parse")
        t.elapsed = 1.5
        report = profiler.report(total_seconds=2.0)
        assert report.stages["parse"] == 1.5
        assert report.total_seconds == 2.0

    def test_report_includes_memory_delta(self) -> None:
        profiler = Profiler()
        profiler._snapshots = [
            MemorySnapshot(rss_mb=50.0, vms_mb=100.0),
            MemorySnapshot(rss_mb=70.0, vms_mb=120.0),
        ]
        report = profiler.report()
        assert report.memory_delta_mb == 20.0

    def test_report_no_snapshots(self) -> None:
        profiler = Profiler()
        report = profiler.report(total_seconds=1.0)
        assert report.memory_delta_mb == 0.0
        assert report.memory_peak_mb == 0.0


class TestBuildMetrics:
    def test_defaults(self) -> None:
        bm = BuildMetrics()
        assert bm.files_total == 0
        assert bm.files_succeeded == 0
        assert bm.files_failed == 0
        assert bm.files_skipped == 0
        assert bm.errors == []
        assert bm.warnings == []

    def test_success_rate(self) -> None:
        bm = BuildMetrics(files_total=10, files_succeeded=7)
        assert bm.success_rate == 70.0

    def test_success_rate_zero_total(self) -> None:
        bm = BuildMetrics()
        assert bm.success_rate == 0.0

    def test_duration_ms(self) -> None:
        bm = BuildMetrics(duration_seconds=3.0)
        assert bm.duration_ms == 3000.0

    def test_to_dict(self) -> None:
        bm = BuildMetrics(files_total=5, files_succeeded=4, files_failed=1)
        d = bm.to_dict()
        assert d["files_total"] == 5
        assert d["files_succeeded"] == 4
        assert d["files_failed"] == 1
        assert d["success_rate"] == 80.0


class TestExecutionReport:
    def test_defaults(self) -> None:
        er = ExecutionReport()
        assert isinstance(er.build, BuildMetrics)
        assert er.conversions == []
        assert er.metadata == {}

    def test_to_dict(self) -> None:
        er = ExecutionReport(
            build=BuildMetrics(files_total=3, files_succeeded=2),
            conversions=[ConversionReport(source_format="md")],
            metadata={"started": "2025-01-01"},
        )
        d = er.to_dict()
        assert d["build"]["files_total"] == 3
        assert len(d["conversions"]) == 1
        assert d["conversions"][0]["source_format"] == "md"
        assert d["metadata"]["started"] == "2025-01-01"


class TestMetricsCollector:
    def test_add_and_reports(self) -> None:
        collector = MetricsCollector()
        r1 = ConversionReport(source_format="md")
        r2 = ConversionReport(source_format="html")
        collector.add(r1)
        collector.add(r2)
        assert len(collector.reports) == 2

    def test_total_time(self) -> None:
        collector = MetricsCollector()
        r1 = ConversionReport()
        r1.metrics.total_time = 2.0
        r2 = ConversionReport()
        r2.metrics.total_time = 3.0
        collector.add(r1)
        collector.add(r2)
        assert collector.total_time == 5.0

    def test_total_input_size(self) -> None:
        collector = MetricsCollector()
        r1 = ConversionReport()
        r1.metrics.input_size = 1000
        r2 = ConversionReport()
        r2.metrics.input_size = 2000
        collector.add(r1)
        collector.add(r2)
        assert collector.total_input_size == 3000

    def test_total_output_size(self) -> None:
        collector = MetricsCollector()
        r1 = ConversionReport()
        r1.metrics.output_size = 500
        collector.add(r1)
        assert collector.total_output_size == 500

    def test_success_count(self) -> None:
        collector = MetricsCollector()
        collector.add(ConversionReport(success=True))
        collector.add(ConversionReport(success=False))
        collector.add(ConversionReport(success=True))
        assert collector.success_count == 2
        assert collector.failure_count == 1

    def test_to_dict(self) -> None:
        collector = MetricsCollector()
        collector.add(ConversionReport(source_format="md", success=True))
        collector.add(ConversionReport(source_format="html", success=False))
        d = collector.to_dict()
        assert d["total_conversions"] == 2
        assert d["successful"] == 1
        assert d["failed"] == 1

    def test_to_build_metrics(self) -> None:
        collector = MetricsCollector()
        collector.add(ConversionReport(success=True))
        collector.add(ConversionReport(success=True))
        collector.add(ConversionReport(success=False))
        bm = collector.to_build_metrics()
        assert bm.files_total == 3
        assert bm.files_succeeded == 2
        assert bm.files_failed == 1


class TestProfileConversion:
    def test_successful_conversion(self) -> None:
        def add(a: int, b: int) -> int:
            return a + b

        result, report = profile_conversion(add, 2, 3)
        assert result == 5
        assert isinstance(report, ConversionReport)
        assert report.success is True
        assert report.total_seconds >= 0

    def test_failed_conversion(self) -> None:
        def broken() -> None:
            msg = "intentional failure"
            raise ValueError(msg)

        result, report = profile_conversion(broken)
        assert result is None
        assert isinstance(report, ConversionReport)
        assert report.success is True  # no success flag updated
        assert len(report.errors) == 1
        assert "intentional failure" in report.errors[0]


class TestMeasureTime:
    def test_returns_result_and_elapsed(self) -> None:
        result, elapsed = measure_time(lambda: 42)
        assert result == 42
        assert isinstance(elapsed, float)
        assert elapsed >= 0

    def test_works_with_args(self) -> None:
        def add(a: int, b: int) -> int:
            return a + b

        result, elapsed = measure_time(add, 3, 4)
        assert result == 7
        assert elapsed >= 0

    def test_works_with_kwargs(self) -> None:
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        result, elapsed = measure_time(greet, "World", greeting="Hi")
        assert result == "Hi, World!"
        assert elapsed >= 0
