"""PiMD — Professional document publishing platform.

Library-first. CLI-second.

Usage::

    from pimd import PiMD

    engine = PiMD()

    # File to file
    engine.md_to_docx("input.md", "output.docx")

    # Text to bytes (no filesystem writes)
    docx_bytes = engine.md_text_to_docx_bytes("# Hello")

    # Async
    await engine.async_md_to_docx("input.md", "output.docx")

Enterprise features::

    from pimd.pipeline import Pipeline, PipelineManager
    from pimd.jobs import JobManager
    from pimd.project import ProjectConverter
    from pimd.config import Config
"""

from pimd.analyzer import AnalysisIssue, AnalysisReport, ProjectAnalyzer
from pimd.api import PiMD
from pimd.attachments import Attachment, AttachmentConfig, AttachmentType
from pimd.batch import BatchProcessor
from pimd.books import BookCompiler, BookConfig
from pimd.branding import Brand, BrandConfig, BrandingManager
from pimd.caching import CacheBackend, MemoryCache
from pimd.caching.redis_cache import (
    RedisCacheBackend,
    RedisDiagramCache,
    RedisEquationCache,
    redis_available,
)

# New modules — engine features
from pimd.callouts import CalloutBlock, CalloutConfig, CalloutType
from pimd.citations import CitationEngine, CitationEntry, CitationStyle

# New modules — ecosystem compatibility
from pimd.compatibility import CompatibilityLayer, FlavorDetectionResult, MarkdownFlavor
from pimd.config import Config
from pimd.converters.html import HTMLConverter, html_to_docx
from pimd.converters.markdown import MarkdownConverter
from pimd.deprecation import deprecate_parameter, deprecated
from pimd.diagrams import DiagramEngine, DiagramRegistry
from pimd.diagrams.models import DIAGRAM_LANGUAGES, DiagramConfig
from pimd.docusaurus import DocusaurusConfig, DocusaurusProject, DocusaurusProjectConverter
from pimd.equations import EquationConfig, EquationEngine, EquationResult
from pimd.exceptions import ConversionError, ParserError, PiMDError, RendererError
from pimd.export import ExportConverter, ExportFormat, ExportOptions
from pimd.footnotes import FootnoteCollection, FootnoteConfig, FootnoteDefinition
from pimd.frontmatter import FrontmatterFormat, Metadata, parse_frontmatter
from pimd.github import GitHubFeaturesConfig, GitHubFeaturesProcessor
from pimd.incremental import IncrementalBuildTracker
from pimd.jobs import JobManager, JobResult, JobStatus
from pimd.layout import DEFAULT_LAYOUT, DocumentLayoutConfig, Margins, PageSize
from pimd.merge import DocumentMerger
from pimd.mkdocs_ import MkDocsConfig, MkDocsProject, MkDocsProjectConverter
from pimd.models import DocumentStatistics
from pimd.obsidian import ObsidianNote, VaultConfig, VaultExporter
from pimd.parallel import (
    BatchSummary,
    ParallelExecutor,
    ParallelResult,
    ProcessExecutor,
    ThreadExecutor,
    parallel_batch,
    parallel_map,
)
from pimd.pipeline import (
    ExportStage,
    ParseStage,
    Pipeline,
    PipelineContext,
    PipelineManager,
    PipelineStage,
    PostProcessStage,
    RenderStage,
    StageType,
    TransformStage,
)
from pimd.profiles import ExportProfile, ProfileManager, ProfileType
from pimd.profiling import ConversionReport, PipelineProfile, Profiler, Timer
from pimd.project import ProjectConverter, ProjectResult
from pimd.recovery import RecoveryContext, RecoveryReport, RecoveryWarning
from pimd.reports import ReportConfig, ReportEngine, ReportType

# New modules — project-level
from pimd.repository import RepoResult, RepositoryConfig, RepoType
from pimd.safety import SafetyError, SafetyGuard, SafetyLimits
from pimd.sphinx import RSTtoMarkdownConverter, SphinxConfig, SphinxProject, SphinxProjectConverter
from pimd.streaming import ChunkProcessor, LargeFileHandler, StreamingMarkdownReader
from pimd.templates import Template, TemplateConfig, TemplateManager, TemplateType
from pimd.themes import ProfessionalTheme, Theme
from pimd.validation import DocumentValidator

__all__ = [
    # Core
    "PiMD",
    "MarkdownConverter",
    "HTMLConverter",
    "md_to_docx",
    "html_to_docx",
    "DocumentStatistics",
    # Themes
    "Theme",
    "ProfessionalTheme",
    # Exceptions
    "PiMDError",
    "ConversionError",
    "ParserError",
    "RendererError",
    # Diagrams
    "DiagramEngine",
    "DiagramRegistry",
    "DiagramConfig",
    "DIAGRAM_LANGUAGES",
    # Equations
    "EquationEngine",
    "EquationConfig",
    "EquationResult",
    # Templates
    "TemplateManager",
    "Template",
    "TemplateConfig",
    "TemplateType",
    # Branding
    "BrandingManager",
    "Brand",
    "BrandConfig",
    # Export
    "ExportConverter",
    "ExportFormat",
    "ExportOptions",
    # Reports
    "ReportEngine",
    "ReportConfig",
    "ReportType",
    # Books
    "BookCompiler",
    "BookConfig",
    # Citations
    "CitationEngine",
    "CitationEntry",
    "CitationStyle",
    # Merge
    "DocumentMerger",
    # Batch
    "BatchProcessor",
    # Validation
    "DocumentValidator",
    # Layout / defaults
    "DocumentLayoutConfig",
    "DEFAULT_LAYOUT",
    "Margins",
    "PageSize",
    # Pipeline
    "Pipeline",
    "PipelineStage",
    "PipelineContext",
    "PipelineManager",
    "StageType",
    "ParseStage",
    "TransformStage",
    "RenderStage",
    "ExportStage",
    "PostProcessStage",
    # Parallel
    "ParallelExecutor",
    "ThreadExecutor",
    "ProcessExecutor",
    "ParallelResult",
    "BatchSummary",
    "parallel_map",
    "parallel_batch",
    # Redis
    "RedisCacheBackend",
    "RedisDiagramCache",
    "RedisEquationCache",
    "redis_available",
    # Cache
    "CacheBackend",
    "MemoryCache",
    # Jobs
    "JobManager",
    "JobStatus",
    "JobResult",
    # Profiling
    "Profiler",
    "Timer",
    "ConversionReport",
    "PipelineProfile",
    # Project
    "ProjectConverter",
    "ProjectResult",
    # Streaming
    "LargeFileHandler",
    "ChunkProcessor",
    "StreamingMarkdownReader",
    # Incremental
    "IncrementalBuildTracker",
    # Config
    "Config",
    # Safety
    "SafetyGuard",
    "SafetyLimits",
    "SafetyError",
    # Recovery
    "RecoveryContext",
    "RecoveryReport",
    "RecoveryWarning",
    # Deprecation
    "deprecated",
    "deprecate_parameter",
    # Ecosystem compatibility
    "MarkdownFlavor",
    "FlavorDetectionResult",
    "CompatibilityLayer",
    "FrontmatterFormat",
    "Metadata",
    "parse_frontmatter",
    "GitHubFeaturesConfig",
    "GitHubFeaturesProcessor",
    "MkDocsConfig",
    "MkDocsProject",
    "MkDocsProjectConverter",
    "DocusaurusConfig",
    "DocusaurusProject",
    "DocusaurusProjectConverter",
    "ObsidianNote",
    "VaultConfig",
    "VaultExporter",
    "RSTtoMarkdownConverter",
    "SphinxConfig",
    "SphinxProject",
    "SphinxProjectConverter",
    # Callout engine
    "CalloutBlock",
    "CalloutConfig",
    "CalloutType",
    # Footnotes
    "FootnoteCollection",
    "FootnoteConfig",
    "FootnoteDefinition",
    # Attachments
    "Attachment",
    "AttachmentConfig",
    "AttachmentType",
    # Repository
    "RepositoryConfig",
    "RepoResult",
    "RepoType",
    # Analyzer
    "AnalysisIssue",
    "AnalysisReport",
    "ProjectAnalyzer",
    # Profiles
    "ExportProfile",
    "ProfileManager",
    "ProfileType",
]

__version__ = "1.0.0"
__author__ = "PiMD Contributors"
__description__ = "Professional document publishing platform"


def md_to_docx(input_file: str, output_file: str) -> None:
    """Convenience function — convert a Markdown file to DOCX in one call.

    Args:
        input_file: Path to the input ``.md`` file.
        output_file: Path where the output ``.docx`` will be written.
    """
    MarkdownConverter().convert(input_file, output_file)
