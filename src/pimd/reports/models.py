"""Report data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ReportType(str, Enum):
    """Supported report categories."""

    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    AUDIT = "audit"
    PROJECT = "project"
    RESEARCH = "research"


@dataclass
class ReportSection:
    """A named section within a report."""

    title: str
    content: str
    level: int = 1
    subsections: list[ReportSection] = field(default_factory=list)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    type: ReportType = ReportType.EXECUTIVE
    title: str = ""
    subtitle: str = ""
    author: str = ""
    company: str = ""
    date: str = ""
    version: str = "1.0.0"
    template: str = "professional"
    brand: str = ""
    generate_toc: bool = True
    page_numbers: bool = True
    cover_page: bool = True
    watermark: str = ""
    output_dir: str = ""
    include_executive_summary: bool = True
    include_references: bool = True
    include_appendices: bool = False
    sections: list[ReportSection] = field(default_factory=list)


_SECTION_TEMPLATES: dict[ReportType, list[tuple[str, str, list[str]]]] = {
    ReportType.EXECUTIVE: [
        (
            "Executive Summary",
            "High-level overview of key findings and recommendations.",
            [
                "Background",
                "Key Findings",
                "Recommendations",
                "Next Steps",
            ],
        ),
        ("Situation Analysis", "Current state assessment.", []),
        ("Proposed Strategy", "Strategic recommendations.", []),
        ("Financial Impact", "Cost-benefit analysis and projections.", []),
        ("Risk Assessment", "Key risks and mitigation strategies.", []),
    ],
    ReportType.TECHNICAL: [
        ("Introduction", "Scope and objectives.", []),
        (
            "System Overview",
            "Architecture and components.",
            [
                "Architecture",
                "Components",
                "Interfaces",
            ],
        ),
        ("Methodology", "Approach and methods.", []),
        ("Implementation", "Implementation details.", []),
        ("Results", "Outcomes and analysis.", []),
        ("Conclusions", "Summary and recommendations.", []),
    ],
    ReportType.AUDIT: [
        ("Executive Summary", "Audit overview and key findings.", []),
        ("Scope and Objectives", "Audit scope and methodology.", []),
        (
            "Findings and Observations",
            "Detailed audit findings.",
            [
                "Control Environment",
                "Risk Management",
                "Compliance",
            ],
        ),
        ("Recommendations", "Action items and remediation.", []),
        ("Management Response", "Response from audited entity.", []),
    ],
    ReportType.PROJECT: [
        ("Project Overview", "Project goals and scope.", []),
        ("Timeline and Milestones", "Key dates and deliverables.", []),
        ("Resources", "Team, budget, and tools.", []),
        ("Progress Update", "Current status and achievements.", []),
        ("Risks and Issues", "Open risks and mitigation.", []),
        ("Next Steps", "Upcoming milestones.", []),
    ],
    ReportType.RESEARCH: [
        ("Abstract", "Brief summary of research.", []),
        ("Introduction", "Background and research questions.", []),
        ("Literature Review", "Related work.", []),
        ("Methodology", "Research methods.", []),
        ("Results", "Findings and data.", []),
        ("Discussion", "Interpretation of results.", []),
        ("Conclusion", "Summary and future work.", []),
        ("References", "Cited works.", []),
    ],
}


def get_section_template(report_type: ReportType) -> list[ReportSection]:
    """Get the default section structure for a report type."""
    sections_data = _SECTION_TEMPLATES.get(report_type, [])
    result: list[ReportSection] = []
    for title, desc, subs in sections_data:
        sub_sections = [ReportSection(title=stitle, content="", level=2) for stitle in subs]
        result.append(
            ReportSection(
                title=title,
                content=f"\n\n{desc}\n\n",
                level=1,
                subsections=sub_sections,
            )
        )
    return result
