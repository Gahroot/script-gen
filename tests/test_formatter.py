from app.formatter import format_markdown


class TestFormatMarkdown:
    """Tests for markdown output formatting."""

    def test_contains_header(self, sample_intake, sample_scripts):
        md = format_markdown(sample_scripts, sample_intake)
        assert "ACME ROOFING - 300 VIDEO ADS" in md
        assert "BATCH CONTENT TELEPROMPTER" in md

    def test_contains_all_hooks(self, sample_intake, sample_scripts):
        md = format_markdown(sample_scripts, sample_intake)
        for i in range(50):
            assert f"Hook number {i}" in md
        assert md.count("**HOOK ") == 50

    def test_contains_all_meats(self, sample_intake, sample_scripts):
        md = format_markdown(sample_scripts, sample_intake)
        for meat in sample_scripts.meats:
            assert meat in md
        assert md.count("## MEAT ") == 3

    def test_contains_all_ctas(self, sample_intake, sample_scripts):
        md = format_markdown(sample_scripts, sample_intake)
        for cta in sample_scripts.ctas:
            assert cta in md
        assert md.count("**CTA ") == 2

    def test_contains_quick_reference(self, sample_intake, sample_scripts):
        md = format_markdown(sample_scripts, sample_intake)
        assert "QUICK REFERENCE" in md
        assert "50 × 3 × 2 = 300 ads" in md
        assert sample_intake.offer in md

    def test_contains_filming_tips(self, sample_intake, sample_scripts):
        md = format_markdown(sample_scripts, sample_intake)
        assert "FILMING TIPS" in md
        assert "teleprompter" in md.lower()
