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

from __future__ import annotations

from pathlib import Path
from typing import Any

from pimd.accessibility import AccessibilityEngine, AccessibilityReport
from pimd.analyzer import AnalysisIssue, AnalysisReport, ProjectAnalyzer
from pimd.api import PiMD

# New modules — API lifecycle & ecosystem
from pimd.api_stability import (
    ApiStatus,
    beta,
    deprecated,
    experimental,
    get_api_alternative,
    get_api_removal,
    get_api_since,
    get_api_status,
    internal,
    stable,
)
from pimd.attachments import Attachment, AttachmentConfig, AttachmentType
from pimd.batch import BatchProcessor
from pimd.books import BookCompiler, BookConfig
from pimd.branding import Brand, BrandConfig, BrandingManager
from pimd.caching import CacheBackend, CacheMetricsCollector, CacheStats, FileSystemCache, MemoryCache
from pimd.caching.redis_cache import (
    RedisCacheBackend,
    RedisDiagramCache,
    RedisEquationCache,
    redis_available,
)

# New modules — unified cache
from pimd.caching.unified import UnifiedCacheManager, UnifiedCacheStats, get_cache, reset_cache

# New modules — engine features
from pimd.callouts import CalloutBlock, CalloutConfig, CalloutType
from pimd.citations import CitationEngine, CitationEntry, CitationStyle

# New modules — ecosystem compatibility
from pimd.compatibility import CompatibilityLayer, FlavorDetectionResult, MarkdownFlavor
from pimd.config import Config, ConfigSchemaEntry
from pimd.converters.html import HTMLConverter, html_to_docx
from pimd.converters.markdown import MarkdownConverter
from pimd.deprecation import deprecate_parameter
from pimd.diagrams import (
    DIAGRAM_LANGUAGES,
    DiagramEngine,
    DiagramRegistry,
    RenderResult,
    clear_cache,
    detect_language,
    doctor,
    get_diagram_renderer,
    get_supported_languages,
    is_supported_language,
    list_diagram_renderers,
    register_diagram_renderer,
    render_diagram,
    render_many_diagrams,
)
from pimd.diagrams.models import DiagramConfig
from pimd.docusaurus import DocusaurusConfig, DocusaurusProject, DocusaurusProjectConverter
from pimd.equations import EquationConfig, EquationEngine, EquationResult
from pimd.exceptions import (
    CacheError,
    ConfigError,
    ConversionError,
    DiagramError,
    ParserError,
    PiMDError,
    PluginError,
    RendererError,
    SecurityError,
)
from pimd.export import ExportConverter, ExportFormat, ExportOptions
from pimd.export.formats.epub import EpubRenderer, validate_epub
from pimd.export.formats.latex import LatexRenderer
from pimd.footnotes import FootnoteCollection, FootnoteConfig, FootnoteDefinition
from pimd.frontmatter import FrontmatterFormat, Metadata, parse_frontmatter
from pimd.github import GitHubFeaturesConfig, GitHubFeaturesProcessor
from pimd.i18n import (
    LanguageConfig,
    ScriptType,
    detect_script,
    get_language_config,
    is_cjk_language,
    is_rtl_language,
    process_text_for_language,
)
from pimd.incremental import IncrementalBuildTracker
from pimd.jobs import JobManager, JobResult, JobStatus
from pimd.layout import DEFAULT_LAYOUT, DocumentLayoutConfig, Margins, PageSize
from pimd.merge import DocumentMerger
from pimd.mkdocs_ import MkDocsConfig, MkDocsProject, MkDocsProjectConverter
from pimd.models import DocumentStatistics
from pimd.observability import BuildMetrics, ConversionReport, ExecutionReport, MetricsCollector, PipelineProfile, Profiler, Timer
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
from pimd.plugins import PLUGIN_TYPES, PluginMetadata
from pimd.profiles import ExportProfile, ProfileManager, ProfileType
from pimd.project import ProjectConverter, ProjectResult
from pimd.recovery import RecoveryContext, RecoveryReport, RecoveryWarning

# New modules — capability registry
from pimd.registry import Capability, CapabilityRegistry, CapabilityType, get_registry, reset_registry
from pimd.remote_assets import RemoteAssetConfig, RemoteAssetManager
from pimd.reports import ReportConfig, ReportEngine, ReportType

# New modules — project-level
from pimd.repository import RepoResult, RepositoryConfig, RepoType
from pimd.revisions import (
    Comment,
    ReviewMetadata,
    Revision,
    RevisionStatus,
    RevisionTracker,
    RevisionType,
)
from pimd.safety import SafetyError, SafetyGuard, SafetyLimits
from pimd.sdk import (
    AssetPlugin,
    BasePlugin,
    CitationPlugin,
    DiagramPlugin,
    Event,
    EventBus,
    ExporterPlugin,
    Hook,
    ParserPlugin,
    PublishingPlugin,
    RendererPlugin,
    TemplatePlugin,
    ValidationPlugin,
)

# New modules — security
from pimd.security import SafeSubprocess, safe_temp_dir, sanitize_svg, sanitize_svg_file, scan_for_secrets, verify_plugin_hash, verify_toml_manifest
from pimd.sphinx import RSTtoMarkdownConverter, SphinxConfig, SphinxProject, SphinxProjectConverter
from pimd.streaming import ChunkProcessor, LargeFileHandler, StreamingMarkdownReader
from pimd.templates import (
    DEFAULT_STYLE_MAP,
    ReferenceDoc,
    ReferenceDocError,
    StyleMapper,
    Template,
    TemplateConfig,
    TemplateManager,
    TemplateType,
    get_available_styles,
    validate_reference_doc,
)
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
    "DiagramError",
    "PluginError",
    "ConfigError",
    "SecurityError",
    "CacheError",
    # API stability
    "ApiStatus",
    "stable",
    "beta",
    "experimental",
    "deprecated",
    "internal",
    "get_api_status",
    "get_api_since",
    "get_api_removal",
    "get_api_alternative",
    # Capability registry
    "CapabilityRegistry",
    "CapabilityType",
    "Capability",
    "get_registry",
    "reset_registry",
    # Unified cache
    "UnifiedCacheManager",
    "UnifiedCacheStats",
    "get_cache",
    "reset_cache",
    # Security
    "sanitize_svg",
    "sanitize_svg_file",
    "verify_plugin_hash",
    "verify_toml_manifest",
    "SafeSubprocess",
    "scan_for_secrets",
    "safe_temp_dir",
    # Diagrams — PiDraw integration
    "DiagramEngine",
    "DiagramRegistry",
    "DiagramConfig",
    "DIAGRAM_LANGUAGES",
    "RenderResult",
    "render_diagram",
    "render_many_diagrams",
    "detect_language",
    "is_supported_language",
    "get_supported_languages",
    "clear_cache",
    "doctor",
    "register_diagram_renderer",
    "get_diagram_renderer",
    "list_diagram_renderers",
    # Equations
    "EquationEngine",
    "EquationConfig",
    "EquationResult",
    # Templates
    "TemplateManager",
    "Template",
    "TemplateConfig",
    "TemplateType",
    "ReferenceDoc",
    "ReferenceDocError",
    "StyleMapper",
    "DEFAULT_STYLE_MAP",
    "get_available_styles",
    "validate_reference_doc",
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
    "FileSystemCache",
    "CacheStats",
    "CacheMetricsCollector",
    # Jobs
    "JobManager",
    "JobStatus",
    "JobResult",
    # Profiling
    "Profiler",
    "Timer",
    "ConversionReport",
    "PipelineProfile",
    "BuildMetrics",
    "ExecutionReport",
    "MetricsCollector",
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
    "ConfigSchemaEntry",
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
    # Accessibility
    "AccessibilityEngine",
    "AccessibilityReport",
    # EPUB
    "EpubRenderer",
    "validate_epub",
    "LatexRenderer",
    # i18n
    "ScriptType",
    "LanguageConfig",
    "detect_script",
    "is_rtl_language",
    "is_cjk_language",
    "get_language_config",
    "process_text_for_language",
    # Collaborative Editing
    "RevisionTracker",
    "Revision",
    "RevisionType",
    "RevisionStatus",
    "Comment",
    "ReviewMetadata",
    # Remote Assets
    "RemoteAssetManager",
    "RemoteAssetConfig",
    # Plugin system
    "PluginMetadata",
    "PLUGIN_TYPES",
    # Extension SDK
    "BasePlugin",
    "DiagramPlugin",
    "TemplatePlugin",
    "CitationPlugin",
    "RendererPlugin",
    "ExporterPlugin",
    "AssetPlugin",
    "ValidationPlugin",
    "ParserPlugin",
    "PublishingPlugin",
    "Hook",
    "Event",
    "EventBus",
]

__version__ = "2.2.4"
__author__ = "PiMD Contributors"
__description__ = "Professional document publishing platform"


def md_to_docx(
    input_file: str,
    output_file: str,
    reference_doc: str | Path | None = None,
    **kwargs: Any,
) -> None:
    """Convenience function — convert a Markdown file to DOCX in one call.

    Args:
        input_file: Path to the input ``.md`` file.
        output_file: Path where the output ``.docx`` will be written.
        reference_doc: Path to a reference ``.docx`` to use as template.
        **kwargs: Additional options passed to :class:`MarkdownConverter`.
    """
    MarkdownConverter(reference_doc=reference_doc).convert(input_file, output_file, **kwargs)
