"""Extended tests for report engine — new report types (compliance, architecture)."""

from pimd.reports.models import ReportConfig, ReportType, get_section_template


class TestReportTypes:
    def test_all_types_present(self) -> None:
        types = list(ReportType)
        values = [t.value for t in types]
        for expected in ["executive", "technical", "audit", "project", "research",
                         "compliance", "architecture"]:
            assert expected in values

    def test_compliance_sections(self) -> None:
        sections = get_section_template(ReportType.COMPLIANCE)
        assert len(sections) > 0
        titles = [s.title for s in sections]
        assert "Executive Summary" in titles
        assert "Control Framework" in titles
        assert "Remediation Plan" in titles

    def test_architecture_sections(self) -> None:
        sections = get_section_template(ReportType.ARCHITECTURE)
        assert len(sections) > 0
        titles = [s.title for s in sections]
        assert "Current State Architecture" in titles
        assert "Target State Architecture" in titles
        assert "Roadmap" in titles

    def test_executive_sections_still_present(self) -> None:
        sections = get_section_template(ReportType.EXECUTIVE)
        assert len(sections) > 0

    def test_report_config_creates(self) -> None:
        config = ReportConfig(
            type=ReportType.COMPLIANCE,
            title="SOC 2 Report",
            author="Auditor",
        )
        assert config.type == ReportType.COMPLIANCE
        assert config.title == "SOC 2 Report"
