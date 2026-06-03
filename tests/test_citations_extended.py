"""Extended tests for citation engine — Harvard style, new features."""

from pimd.citations.engine import CitationEngine, CitationEntry, CitationStyle


class TestHarvardStyle:
    def setup_method(self) -> None:
        self.entry = CitationEntry(
            key="smith2024",
            type="article",
            title="A Study of Document Generation",
            author="Smith, John",
            year="2024",
            journal="Journal of Publishing",
            volume="15",
            pages="100-120",
        )

    def test_harvard_article_format(self) -> None:
        formatted = self.entry.format_harvard()
        assert "Smith, John" in formatted
        assert "(2024)" in formatted
        assert "Journal of Publishing" in formatted
        assert "Vol. 15" in formatted

    def test_harvard_book_format(self) -> None:
        book = CitationEntry(
            key="book2023",
            type="book",
            title="Advanced Publishing",
            author="Doe, Jane",
            year="2023",
            publisher="Academic Press",
            address="New York",
        )
        formatted = book.format_harvard()
        assert "Doe, Jane" in formatted
        assert "(2023)" in formatted
        assert "Academic Press" in formatted
        assert "New York" in formatted

    def test_harvard_dispatch(self) -> None:
        formatted = self.entry.format(CitationStyle.HARVARD)
        assert "Smith, John" in formatted


class TestCitationStyleEnum:
    def test_harvard_in_enum(self) -> None:
        assert CitationStyle.HARVARD.value == "harvard"

    def test_all_styles_present(self) -> None:
        styles = list(CitationStyle)
        names = [s.value for s in styles]
        for expected in ["apa", "ieee", "mla", "chicago", "harvard"]:
            assert expected in names


class TestCitationEngineExtended:
    def test_harvard_citation_output(self) -> None:
        engine = CitationEngine()
        engine._entries["key2024"] = CitationEntry(
            key="key2024",
            title="Test",
            author="Author, A.",
            year="2024",
        )
        result = engine.cite("key2024", CitationStyle.HARVARD)
        assert "Author, A." in result
        assert "2024" in result

    def test_bibliography_harvard(self) -> None:
        engine = CitationEngine()
        engine._entries["test"] = CitationEntry(
            key="test",
            title="Test Title",
            author="Writer, B.",
            year="2024",
        )
        bib = engine.bibliography(CitationStyle.HARVARD)
        assert "Writer, B." in bib
        assert "(2024)" in bib
