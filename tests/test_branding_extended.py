"""Extended tests for branding — watermark types, cover config, brand models."""

from pimd.branding.models import Brand, BrandConfig, BrandMetadata
from pimd.branding.watermarks import WatermarkConfig, WatermarkType


class TestWatermarkTypes:
    def test_public_type_exists(self) -> None:
        assert WatermarkType.PUBLIC.value == "PUBLIC"

    def test_all_types_present(self) -> None:
        types = list(WatermarkType)
        values = [t.value for t in types]
        for expected in ["CONFIDENTIAL", "DRAFT", "INTERNAL", "PUBLIC", "CUSTOM"]:
            assert expected in values

    def test_watermark_config_defaults(self) -> None:
        config = WatermarkConfig()
        assert config.text == "DRAFT"
        assert config.type == WatermarkType.DRAFT
        assert config.enabled

    def test_watermark_config_public(self) -> None:
        config = WatermarkConfig(type=WatermarkType.PUBLIC)
        assert config.type == WatermarkType.PUBLIC


class TestBrand:
    def test_brand_creation(self) -> None:
        brand = Brand(
            name="Acme Corp",
            metadata=BrandMetadata(
                title="Annual Report",
                company="Acme Corp",
                author="John Doe",
                version="2.0.0",
            ),
            config=BrandConfig(
                primary_color="1F4E79",
                font_family="Arial",
                logo_path="/path/to/logo.png",
                website="https://acme.example.com",
            ),
        )
        assert brand.name == "Acme Corp"
        assert brand.metadata.company == "Acme Corp"
        assert brand.config.primary_color == "1F4E79"

    def test_brand_logo_abs_path_none(self) -> None:
        brand = Brand(name="Test")
        assert brand.logo_abs_path is None

    def test_brand_logo_abs_path_with_relative(self) -> None:
        brand = Brand(
            name="Test",
            config=BrandConfig(logo_path="relative/logo.png"),
        )
        path = brand.logo_abs_path
        assert path is None or not path.exists()
