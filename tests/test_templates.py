"""Tests for template system: inheritance, new template types, validation."""

import json
from pathlib import Path

from pimd.templates import TemplateManager, TemplateType
from pimd.templates.inheritance import TemplateInheritance
from pimd.templates.models import Template, TemplateConfig, TemplateMetadata


class TestTemplateTypes:
    def test_all_types_present(self) -> None:
        types = list(TemplateType)
        names = [t.value for t in types]
        for expected in ["professional", "academic", "technical", "business", "book",
                         "proposal", "invoice", "resume", "manual", "api", "custom"]:
            assert expected in names

    def test_template_manager_finds_presets(self) -> None:
        mgr = TemplateManager()
        templates = mgr.list_templates()
        template_names = [t.name for t in templates]
        assert len(template_names) > 0, "Expected at least one template preset"


class TestTemplateInheritance:
    def test_empty_chain(self) -> None:
        inheritance = TemplateInheritance()
        chain = inheritance.resolve_chain("nonexistent_template")
        assert chain.depth == 0
        assert chain.leaf is None

    def test_merge_configs_empty(self) -> None:
        inheritance = TemplateInheritance()
        merged = inheritance.merge_configs()
        assert merged.default_font == "Calibri"
        assert merged.default_font_size == 11

    def test_merge_configs_override(self) -> None:
        inheritance = TemplateInheritance()
        base = TemplateConfig(default_font="Times New Roman", page_size="Letter")
        override = TemplateConfig(default_font="Arial", generate_toc=True)
        merged = inheritance.merge_configs(base, override)
        assert merged.default_font == "Arial"
        assert merged.page_size == "Letter"
        assert merged.generate_toc

    def test_create_child_template(self) -> None:
        inheritance = TemplateInheritance()
        parent = Template(
            metadata=TemplateMetadata(name="base_professional", type=TemplateType.PROFESSIONAL),
            config=TemplateConfig(default_font="Calibri", page_size="A4", generate_toc=True),
        )
        inheritance._cache["base_professional"] = parent
        child = inheritance.create_child("base_professional", "my_child", {"default_font": "Arial"})
        assert child.name == "my_child"
        assert child.config.default_font == "Arial"
        assert child.config.page_size == "A4"
        assert child.config.generate_toc

    def test_merge_chain_with_single(self) -> None:
        inheritance = TemplateInheritance()
        tpl = Template(
            metadata=TemplateMetadata(name="test", type=TemplateType.TECHNICAL),
            config=TemplateConfig(default_font="Courier"),
        )
        from pimd.templates.inheritance import InheritanceChain
        chain = InheritanceChain(names=["test"], resolved=[tpl])
        merged = inheritance.merge_chain(chain)
        assert merged.config.default_font == "Courier"
        assert merged.name == "test"

    def test_merge_chain_with_multiple(self) -> None:
        inheritance = TemplateInheritance()
        base = Template(
            metadata=TemplateMetadata(name="base", type=TemplateType.PROFESSIONAL),
            config=TemplateConfig(default_font="Calibri", page_size="A4", generate_toc=False),
        )
        child = Template(
            metadata=TemplateMetadata(name="child", type=TemplateType.TECHNICAL),
            config=TemplateConfig(default_font="Consolas", generate_toc=True),
        )
        from pimd.templates.inheritance import InheritanceChain
        chain = InheritanceChain(names=["base", "child"], resolved=[base, child])
        merged = inheritance.merge_chain(chain)
        assert merged.config.default_font == "Consolas"
        assert merged.config.page_size == "A4"
        assert merged.config.generate_toc


class TestTemplatePresets:
    def test_proposal_template_config(self) -> None:
        config_path = Path(__file__).parent.parent / "src" / "pimd" / "templates" / "presets" / "proposal" / "template.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
            assert data["type"] == "proposal"
            assert data["config"]["generate_toc"]

    def test_api_template_config(self) -> None:
        config_path = Path(__file__).parent.parent / "src" / "pimd" / "templates" / "presets" / "api" / "template.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
            assert data["type"] == "api"
            assert data["config"]["default_font"] == "Consolas"
