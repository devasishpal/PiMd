# Roadmap

## PiMD Post-2.0 Development Roadmap

This document outlines the planned development trajectory for PiMD beyond the v2.0.0 release. Timelines are approximate and subject to change.

---

## v2.1 — Web API & REST Server (Target: Q3 2026)

### Web API
- Built-in REST API server (`pimd serve`)
- OpenAPI/Swagger documentation
- Job queue with status polling
- Webhook notifications on conversion completion

### REST Endpoints
- `POST /convert` — Submit conversion jobs
- `GET /jobs/{id}` — Poll job status and download results
- `GET /templates` — List available templates
- `POST /validate` — Validate documents without conversion
- `GET /health` — Server health check

### Additional
- Rate limiting and API key authentication
- Concurrent job processing with configurable worker pools
- Docker images for easy deployment
- Health monitoring dashboard
- Prometheus metrics export

---

## v2.2 — Collaborative Editing (Target: Q1 2027)

### Real-time Collaboration
- Document state synchronization
- Operational transform for concurrent editing
- WebSocket-based live preview
- Comment/annotation support

### Document Management
- Version history and diff viewer
- Document locking and access control
- Multi-user session management
- Conflict resolution strategies

### Integration
- Google Drive and SharePoint connectors
- Git-based document synchronization
- WebDAV support
- CI/CD integration for automated doc generation

---

## v3.0 — Plugin Marketplace & Distributed Builds (Target: Q4 2027)

### Plugin Marketplace
- Public plugin registry and index
- `pimd plugin search`, `pimd plugin publish`
- Plugin versioning and dependency management
- Community plugin submission workflow
- Plugin sandboxing for security

### Distributed Builds
- Multi-machine build orchestration
- Redis-backed task distribution
- Build graph with dependency resolution
- Incremental builds across machines
- Artifact caching and sharing

### Enterprise Features
- LDAP/SSO authentication
- Audit logging and compliance reporting
- Document signing and certification
- Tenant isolation for multi-org deployments
- SLA-based job prioritization

### Platform Expansion
- Native Windows/macOS/Linux desktop app (Tauri/Electron)
- VS Code extension for inline preview
- GitHub Actions and GitLab CI official actions
- Pre-built binaries for all platforms

---

## Long-term Vision

### Format Expansion
- EPUB 3 support with accessibility metadata
- LaTeX direct rendering (not via SVG fallback)
- Markdown to Markdown (format normalization)
- ODF (OpenDocument) format support
- PDF/A archival format generation

### AI-Assisted Features
- Smart diagram layout optimization
- Automated alt-text generation for accessibility
- Content summarization
- Translation support (document-level)

### Performance
- Native Rust extensions for parsing and rendering
- WASM-based in-browser preview
- Zero-copy document model for large files
- Memory-mapped file handling for multi-GB documents

---

## How to Influence the Roadmap

- **Vote on issues**: Comment with 👍 on GitHub issues you care about
- **Sponsor development**: Consider sponsoring via GitHub Sponsors
- **Contribute code**: PRs are welcome for any of these features
- **Provide feedback**: Open a discussion or feature request

We prioritize features based on community interest, maintainability, and alignment with PiMD's mission of being the best document conversion framework for developers.
