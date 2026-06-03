# Support

## GitHub Issues

Bug reports and feature requests are tracked on GitHub:

- **Bug report**: https://github.com/devasishpal/PiMd/issues/new?template=bug_report.md
- **Feature request**: https://github.com/devasishpal/PiMd/issues/new?template=feature_request.md
- **View all issues**: https://github.com/devasishpal/PiMd/issues

### Before Opening an Issue

1. Check the [FAQ](#faq) below for common questions.
2. Search existing issues to see if it has already been reported.
3. Run `pimd doctor` to check your system configuration.
4. Include the output of `pimd version` and `pimd doctor` in your report.

## Documentation

- **README**: https://github.com/devasishpal/PiMd#readme
- **CLI Help**: Run `pimd --help` for a full list of commands
- **API Reference**: Run `python -c "import pimd; help(pimd.PiMD)"`
- **Examples**: See the `examples/` directory in the repository
- **Changelog**: See `CHANGELOG.md` for version history

## Community

- **GitHub Discussions**: https://github.com/devasishpal/PiMd/discussions
- **Contributing**: See `CONTRIBUTING.md` for how to contribute code

## FAQ

### What is PiMD?

PiMD is a Python library and CLI tool that converts Markdown and HTML into professional DOCX documents. It supports automatic diagram rendering (Mermaid, PlantUML, Graphviz, D2, and more), LaTeX equations as editable OMML, templates, themes, branding, and enterprise safety features.

### Does PiMD require an internet connection?

No. PiMD is offline-first. All features work without internet access. The only exception is the `RemoteAssetManager` which can download remote images, but this is optional and configurable.

### What Python versions are supported?

Python 3.10, 3.11, 3.12, and 3.13.

### How do I install diagram rendering tools?

Diagram tools must be installed separately. See the [README](README.md) for installation instructions for each tool (Mermaid, PlantUML, Graphviz, D2, etc.).

### How do I create a custom template?

Templates are JSON-based configuration files. Start with `pimd template list` to see available templates, then create your own by extending an existing one.

### How do I write a plugin?

Use the Extension SDK (`pimd.sdk`). See `CONTRIBUTING.md` for the plugin development guide and examples.

### Does PiMD support PDF export?

Yes, via `pimd export pdf`. On Windows it uses `docx2pdf`; on other platforms it uses `weasyprint`.

### Can I use PiMD in a web framework?

Yes. Use the in-memory conversion API (`md_text_to_docx_bytes()`) to convert content to bytes without writing to disk. A FastAPI example is in the README.

### How do I configure PiMD?

Create a `.pimdconfig` file in your project root, or use environment variables prefixed with `PIMD_`. Run `pimd config init` to generate a default configuration file.

### How do I enable caching?

Caching is enabled by default using the in-memory backend. For persistent caching across runs, use the filesystem backend or Redis. See the README for configuration details.

### The `pimd.caching.redis` module requires Redis server?

The Redis cache backend requires a running Redis server. If Redis is not available, PiMD falls back to the memory cache.

### Where are configuration files stored?

- User global: `~/.pimd/config.toml`
- Project local: `.pimdconfig` in the project directory
- Cache directory: `~/.pimd/cache/`

### How do I update from v1.x to v2.0?

See the changelog for breaking changes. The main change is that `pimd.profiling` is deprecated in favor of `pimd.observability`. Configuration files should be updated to use `.pimdconfig` instead of `pimd.toml`.
