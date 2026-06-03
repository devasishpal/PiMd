# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | ✅ Active development |
| 1.1.x   | ✅ Security patches only |
| 1.0.x   | ❌ End of life |
| < 1.0   | ❌ End of life |

## Reporting a Vulnerability

If you discover a security vulnerability in PiMD, please do NOT open a public issue. Instead, report it privately via one of these methods:

1. **GitHub Security Advisory**: Navigate to https://github.com/devasishpal/PiMd/security/advisories/new
2. **Email**: Contact the maintainers directly through GitHub.
3. **Direct message**: Reach out to the repository owner on GitHub.

We will acknowledge receipt within 48 hours and provide an estimated timeline for a fix. Security fixes are prioritized and released as patch versions.

## What to Include

When reporting a vulnerability, please include:

- Description of the vulnerability
- Steps to reproduce
- PiMD version affected
- Python version and operating system
- Any potential impact or exploit scenarios

## Security Practices in PiMD

### SafetyGuard

PiMD includes a built-in safety layer (`pimd.safety`) that enforces limits on:

- **File size**: Maximum input file size (configurable, default 100 MB via `PIMD_SECURITY_MAX_INPUT_SIZE_MB`)
- **Text size**: Maximum text length for in-memory conversion
- **Block count**: Maximum number of document blocks (default 100,000 via `PIMD_SECURITY_MAX_DOCUMENT_BLOCKS`)
- **Nesting depth**: Maximum nesting depth for includes (default 100 via `PIMD_SECURITY_MAX_NESTING_DEPTH`)
- **Image size**: Maximum image file size (default 10 MB via `PIMD_SECURITY_MAX_IMAGE_SIZE_MB`)
- **Path traversal**: Blocked path patterns prevent directory traversal attacks
- **URL scheme whitelisting**: Only allowed URL schemes are processed
- **Null byte detection**: Input is scanned for null byte injection
- **Allowed/blocked paths**: Configure allowlists and blocklists for file include directives

### Safety Profiles

```python
from pimd.safety import SafetyLimits

# Use strict limits (recommended for untrusted input)
limits = SafetyLimits.strict()

# Use permissive limits (for trusted internal documents)
limits = SafetyLimits.permissive()

# Custom limits
limits = SafetyLimits(
    max_input_size_mb=10,
    max_nesting_depth=20,
    max_document_blocks=50000,
    max_image_size_mb=5,
)
```

### SafetyGuard Configuration via Environment Variables

All safety limits can be configured via environment variables:

| Variable | Default | Description |
|---|---|---|
| `PIMD_SECURITY_MAX_INPUT_SIZE_MB` | 100 | Maximum input file size in MB |
| `PIMD_SECURITY_MAX_NESTING_DEPTH` | 100 | Maximum nesting depth |
| `PIMD_SECURITY_MAX_DOCUMENT_BLOCKS` | 100000 | Maximum document blocks |
| `PIMD_SECURITY_MAX_IMAGE_SIZE_MB` | 10 | Maximum image file size |
| `PIMD_SECURITY_ALLOWED_PATHS` | [] | Allowed paths for includes (JSON array) |
| `PIMD_SECURITY_BLOCKED_PATHS` | [] | Blocked paths for includes (JSON array) |

### Remote Asset Security

The `RemoteAssetManager` (`pimd.remote_assets`) provides:

- **Domain allowlists**: Restrict asset downloads to trusted domains
- **SSL verification**: Configurable SSL verification for HTTPS downloads
- **Size limits**: Maximum file size enforcement for downloads
- **Offline mode**: Block all remote requests, use cached assets only
- **SHA256 verification**: Content-addressable caching prevents tampering

### Dependency Security

- All dependencies are pinned via `pyproject.toml` with minimum versions
- Regular dependency updates via Dependabot (if enabled on the repository)
- No cloud or network dependencies in the core package (offline-first)

## Configuration File Security

- Config files (`.pimdconfig`) are project-local and should not contain secrets
- Environment variables (`PIMD_*`) are the recommended way to inject sensitive configuration
- Config file paths are validated to prevent directory traversal

## Plugin Security

- Plugins run with the same privileges as the host process
- Only install plugins from trusted sources
- Review plugin source code before installation
- The Plugin Manager validates plugin metadata on load

## Disclosure Policy

We follow a 90-day disclosure timeline for security vulnerabilities:
1. Reporter submits vulnerability (day 0)
2. We acknowledge and triage (day 0-2)
3. Fix developed and tested (day 1-30)
4. Patch released (day 30)
5. Public disclosure after 90 days, or earlier if a patch is available
