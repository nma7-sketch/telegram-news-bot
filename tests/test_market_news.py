import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from market_news import (
    FEEDS,
    MarketArticle,
    _fingerprints,
    classify_title,
    format_message,
    load_state,
    parse_feed,
    remove_old_history,
    save_state,
    select_article,
)


class MarketNewsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        self.feed = FEEDS[0]

    def make_article(self, title, region='GB', published_at=None, url_suffix='1'):
        feed = next(feed for feed in FEEDS if feed.country_code == region)
        return MarketArticle(
            title=title,
            url=f'https://example.com/market/{url_suffix}',
            published_at=published_at or self.now - timedelta(minutes=10),
            source=feed.name,
            country_code=feed.country_code,
            country_name=feed.country_name,
            flag=feed.flag,
            category=classify_title(title),
        )

    def test_classifies_only_requested_market_topics(self):
        self.assertEqual(classify_title('Oil prices rise as OPEC cuts output'), 'Oil')
        self.assertEqual(classify_title('Bitcoin and crypto prices rally'), 'Crypto')
        self.assertEqual(classify_title('Yen exchange rate moves after central bank decision'), 'Currency')
        self.assertEqual(classify_title('Global stocks fall after earnings report'), 'Stocks')
        self.assertEqual(classify_title('Public Form 4 filing reports insider stock purchase'), 'Stocks')
        self.assertEqual(classify_title('Insider trading investigation follows public filing'), 'Finance')
        self.assertIsNone(classify_title('China should share its renewable energy expertise'))
        self.assertIsNone(classify_title('Oil painting exhibit opens at the museum'))
        self.assertIsNone(classify_title('Dollar Tree shares growth with employees'))
        self.assertIsNone(classify_title('New film wins an international award'))

    def test_feed_parser_keeps_only_relevant_news_within_24_hours(self):
        xml_data = b'''<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item><title>Stocks rise in global trading</title>
            <link>https://example.com/recent</link>
            <pubDate>Sun, 15 Nov 2026 11:00:00 GMT</pubDate>
            <source>Example Markets</source></item>
          <item><title>Oil prices in a historical report</title>
            <link>https://example.com/old</link>
            <pubDate>Fri, 13 Nov 2026 11:00:00 GMT</pubDate></item>
          <item><title>Global film festival opens</title>
            <link>https://example.com/irrelevant</link>
            <pubDate>Sun, 15 Nov 2026 11:30:00 GMT</pubDate></item>
          <item><title>Bitcoin future story</title>
            <link>https://example.com/future</link>
            <pubDate>Mon, 16 Nov 2026 11:00:00 GMT</pubDate></item>
        </channel></rss>'''

        articles = parse_feed(xml_data, self.feed, self.now)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, 'Stocks rise in global trading')
        self.assertEqual(articles[0].source, 'Example Markets')
        self.assertEqual(articles[0].country_code, 'GB')

    def test_atom_feed_is_supported(self):
        xml_data = b'''<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry><title>Bitcoin markets gain</title>
            <link href="https://example.com/crypto" rel="alternate"/>
            <updated>2026-11-15T11:30:00Z</updated></entry>
        </feed>'''

        articles = parse_feed(xml_data, self.feed, self.now)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].category, 'Crypto')

    def test_seen_url_or_title_prevents_repeat(self):
        article = self.make_article('Oil prices rise today')
        repeated_article = self.make_article(
            'Oil prices rise today',
            url_suffix='different-syndicated-url',
        )
        another_article = self.make_article('Crude oil market outlook changes', url_suffix='2')
        state = {fingerprint: self.now.isoformat() for fingerprint in _fingerprints(article)}

        self.assertIsNone(select_article((repeated_article,), state, self.now))
        self.assertEqual(select_article((another_article,), state, self.now), another_article)

    def test_regions_rotate_when_multiple_articles_are_available(self):
        uk_article = self.make_article('UK stocks rise', region='GB', url_suffix='uk')
        india_article = self.make_article('India stocks rally', region='IN', url_suffix='india')
        us_article = self.make_article('US shares gain', region='US', url_suffix='us')

        first = select_article((uk_article, india_article, us_article), {}, self.now)
        next_half_hour = select_article(
            (uk_article, india_article, us_article),
            {},
            self.now + timedelta(minutes=30),
        )

        self.assertNotEqual(first.country_code, next_half_hour.country_code)

    def test_history_expires_after_seven_days_and_round_trips(self):
        fresh = self.now - timedelta(days=1)
        stale = self.now - timedelta(days=8)
        state = {'fresh': fresh.isoformat(), 'stale': stale.isoformat()}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            save_state(state, path)
            loaded = load_state(path)

        pruned = remove_old_history(loaded, self.now)
        self.assertEqual(set(pruned), {'fresh'})

    def test_message_includes_source_region_category_age_and_link(self):
        article = self.make_article('Bitcoin rallies across global markets', region='IN')

        message = format_message(article, self.now)

        self.assertIn('🇮🇳 India source', message)
        self.assertIn('CRYPTO', message)
        self.assertIn('10 min ago', message)
        self.assertIn(article.url, message)
        self.assertIn('Public reporting only', message)


if __name__ == '__main__':
    unittest.main()
