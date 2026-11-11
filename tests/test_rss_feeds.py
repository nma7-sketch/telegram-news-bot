import unittest

from main import parse_rss_feed


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

    def test_ignores_entries_without_valid_titles_or_http_links(self):
        content = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item><title>No link</title></item>
          <item><title>Invalid link</title><link>javascript:alert(1)</link></item>
        </channel></rss>"""

        self.assertEqual(parse_rss_feed(content, "Example"), [])

    def test_rejects_unparseable_feed(self):
        with self.assertRaises(ValueError):
            parse_rss_feed(b"not xml", "Example")


if __name__ == "__main__":
    unittest.main()
