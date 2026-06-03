"""Tests for remote asset management."""



from pimd.remote_assets import RemoteAssetConfig, RemoteAssetManager


class TestRemoteAssetManager:
    def test_is_remote_url(self) -> None:
        mgr = RemoteAssetManager()
        assert mgr.is_remote_url("https://example.com/image.png")
        assert mgr.is_remote_url("http://example.com/image.png")
        assert not mgr.is_remote_url("/local/image.png")
        assert not mgr.is_remote_url("local.png")

    def test_url_to_cache_key(self) -> None:
        key = RemoteAssetManager._url_to_cache_key("https://example.com/image.png")
        assert len(key) == 32
        assert key.isalnum()

    def test_mime_to_extension(self) -> None:
        assert RemoteAssetManager._mime_to_extension("image/png", "") == ".png"
        assert RemoteAssetManager._mime_to_extension("image/jpeg", "") == ".jpg"
        assert RemoteAssetManager._mime_to_extension("image/svg+xml", "") == ".svg"
        assert RemoteAssetManager._mime_to_extension("application/pdf", "") == ".pdf"
        assert RemoteAssetManager._mime_to_extension("font/ttf", "") == ".ttf"
        assert RemoteAssetManager._mime_to_extension("text/plain", "file.xyz") == ".xyz"

    def test_extract_urls_empty(self) -> None:
        mgr = RemoteAssetManager()
        urls = mgr.extract_urls("Just plain text")
        assert urls == []

    def test_extract_urls_markdown(self) -> None:
        mgr = RemoteAssetManager()
        text = "![alt](https://example.com/image.png)"
        urls = mgr.extract_urls(text)
        assert "https://example.com/image.png" in urls

    def test_extract_urls_html(self) -> None:
        mgr = RemoteAssetManager()
        text = '<img src="https://example.com/photo.jpg" />'
        urls = mgr.extract_urls(text)
        assert "https://example.com/photo.jpg" in urls

    def test_cache_directory_created(self) -> None:
        mgr = RemoteAssetManager(config=RemoteAssetConfig(cache_dir="/tmp/pimd-test-remote-cache"))
        assert mgr.cache_dir.exists()
        assert mgr.cache_size() >= 0

    def test_offline_mode_fetch_fails(self) -> None:
        config = RemoteAssetConfig(cache_dir="/tmp/pimd-test-offline", offline_mode=True)
        mgr = RemoteAssetManager(config=config)
        result = mgr.fetch(["https://nonexistent.example.com/image.png"])
        assert len(result.assets) == 1
        assert result.assets[0].error is not None
        assert not result.assets[0].cached
