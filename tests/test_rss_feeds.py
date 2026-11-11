import unittest

from main import build_target_sources, parse_rss_feed


class ParseRssFeedTests(unittest.TestCase):
    def test_parses_rss_items(self):
        content = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><item>
          <title>Market &amp; outlook</title>
          <link>https://example.com/outlook</link>
        </item></channel></rss>"""

        self.assertEqual(
            parse_rss_feed(content, "Example"),
            [{
                "title": "Market & outlook",
                "link": "https://example.com/outlook",
                "source": "Example",
            }],
        )

    def test_parses_atom_entries(self):
        content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom"><entry>
          <title>Fund update</title>
          <link href="https://example.com/update" rel="alternate" />
        </entry></feed>"""

        self.assertEqual(
            parse_rss_feed(content, "Example"),
            [{
                "title": "Fund update",
                "link": "https://example.com/update",
                "source": "Example",
            }],
        )

    def test_ignores_entries_without_printable_titles_or_http_links(self):
        content = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item><title>No link</title></item>
          <item><title>Invalid link</title><link>javascript:alert(1)</link></item>
          <item><title>عنوان عربي</title><link>https://example.com/arabic</link></item>
        </channel></rss>""".encode("utf-8")

        self.assertEqual(parse_rss_feed(content, "Example"), [])

    def test_rejects_unparseable_feed(self):
        with self.assertRaises(ValueError):
            parse_rss_feed(b"not xml", "Example")


class SourceSelectionTests(unittest.TestCase):
    def test_includes_only_managers_above_the_aum_threshold(self):
        sources = [
            ("Above threshold", 501, "https://example.com/above"),
            ("At threshold", 500, "https://example.com/at"),
            ("Below threshold", 499, "https://example.com/below"),
        ]

        self.assertEqual(
            build_target_sources(sources, 500),
            {"Above threshold": "https://example.com/above"},
        )


if __name__ == "__main__":
    unittest.main()
