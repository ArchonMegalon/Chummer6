from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.sync_public_guide_from_design import _render_with_start_here


class RenderWithStartHereTests(unittest.TestCase):
    def test_faq_rewrites_heading_and_body(self) -> None:
        source = """# FAQ

## If you want the behind-the-scenes details

### Where does the deeper plan live?

In the planning notes that shape the roadmap and the public guide.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "FAQ.md"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_with_start_here(source_path, "FAQ.md", "")

        self.assertIn("## If you want more detail", rendered)
        self.assertNotIn("## If you want the behind-the-scenes details", rendered)
        self.assertIn(
            "Start with [Where To Go Deeper](WHERE_TO_GO_DEEPER.md). It points to the optional deeper guide pages without sending most readers through internal planning material first.",
            rendered,
        )
        self.assertNotIn(
            "In the planning notes that shape the roadmap and the public guide.",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
