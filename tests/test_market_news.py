import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from market_news import (
    FEEDS,
    MarketArticle,
    _fingerprints,
    classify_title,
    format_digest,
    load_state,
    parse_feed,
    remove_old_history,
    save_state,
    select_articles,
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

        self.assertEqual(select_articles((repeated_article,), state), ())
        self.assertEqual(select_articles((another_article,), state), (another_article,))

    def test_selects_freshest_unseen_article_for_each_available_region(self):
        uk_older = self.make_article('UK stocks fall', region='GB', url_suffix='uk-old')
        uk_newer = self.make_article(
            'UK stocks rally',
            region='GB',
            published_at=self.now - timedelta(minutes=2),
            url_suffix='uk-new',
        )
        india_article = self.make_article('India stocks rally', region='IN', url_suffix='india')
        us_article = self.make_article('US stocks gain', region='US', url_suffix='us')

        selected = select_articles(
            (us_article, uk_older, india_article, uk_newer),
            {},
        )

        self.assertEqual(
            [(article.country_code, article.title) for article in selected],
            [
                ('GB', 'UK stocks rally'),
                ('IN', 'India stocks rally'),
                ('US', 'US stocks gain'),
            ],
        )

    def test_same_headline_is_included_only_once_in_a_digest(self):
        uk_article = self.make_article('Global stocks rally', region='GB', url_suffix='uk')
        us_duplicate = self.make_article('Global stocks rally', region='US', url_suffix='us')

        selected = select_articles((uk_article, us_duplicate), {})

        self.assertEqual(selected, (uk_article,))

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

    def test_digest_includes_all_selected_regions_in_one_message(self):
        india_article = self.make_article('Bitcoin rallies across markets', region='IN')
        us_article = self.make_article('US stocks gain today', region='US', url_suffix='us')

        messages = format_digest((india_article, us_article), self.now)

        self.assertEqual(len(messages), 1)
        self.assertIn('🇮🇳 India source', messages[0])
        self.assertIn('🇺🇸 US source', messages[0])
        self.assertIn('CRYPTO', messages[0])
        self.assertIn('10 min ago', messages[0])
        self.assertIn(india_article.url, messages[0])
        self.assertIn(us_article.url, messages[0])
        self.assertIn('Public reporting only', messages[0])

    def test_long_digest_splits_below_telegram_limit(self):
        articles = tuple(
            self.make_article(
                f'{region} stocks rally',
                region=region,
                url_suffix=f'{region}-' + ('x' * 1700),
            )
            for region in ('GB', 'IN', 'AU', 'JP', 'HK', 'US', 'GLOBAL')
        )

        messages = format_digest(articles, self.now)

        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(message) <= 4096 for message in messages))

    def test_empty_digest_has_no_messages(self):
        self.assertEqual(format_digest((), self.now), ())


if __name__ == '__main__':
    unittest.main()
