import unittest
from datetime import datetime, timedelta, timezone

from reddit_discovery import (
    RedditPost,
    build_feed_url,
    format_message,
    parse_feed,
    select_post,
)


class RedditDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.posts = tuple(
            RedditPost(
                title=f'Learning {index}',
                url=f'https://www.reddit.com/r/todayilearned/comments/{index}/',
                published='2026-11-14T00:00:00+00:00',
            )
            for index in range(3)
        )

    def test_feed_targets_top_todayilearned_posts(self):
        self.assertEqual(
            build_feed_url(),
            'https://www.reddit.com/r/todayilearned/top/.rss?t=day&limit=30',
        )

    def test_parses_reddit_atom_feed_and_ignores_external_links(self):
        xml_data = b'''<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Useful fact</title>
            <link href="https://www.reddit.com/r/todayilearned/comments/abc/"/>
            <published>2026-11-14T00:00:00+00:00</published>
          </entry>
          <entry>
            <title>Unexpected external link</title>
            <link href="https://example.com/post"/>
          </entry>
        </feed>'''

        self.assertEqual(
            parse_feed(xml_data),
            (
                RedditPost(
                    title='Useful fact',
                    url='https://www.reddit.com/r/todayilearned/comments/abc/',
                    published='2026-11-14T00:00:00+00:00',
                ),
            ),
        )

    def test_post_rotates_every_two_hours_and_wraps(self):
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)

        self.assertEqual(select_post(self.posts, start), (1, self.posts[0]))
        self.assertEqual(select_post(self.posts, start + timedelta(hours=2)), (2, self.posts[1]))
        self.assertEqual(select_post(self.posts, start + timedelta(hours=6)), (1, self.posts[0]))

    def test_selection_is_timezone_independent_and_rejects_naive_time(self):
        utc_time = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        local_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))

        self.assertEqual(select_post(self.posts, utc_time), select_post(self.posts, local_time))
        with self.assertRaises(ValueError):
            select_post(self.posts, datetime(2026, 1, 1))

    def test_empty_posts_and_oversized_titles_are_handled(self):
        with self.assertRaises(ValueError):
            select_post(())

        post = RedditPost(
            title='A' * 900,
            url='https://www.reddit.com/r/todayilearned/comments/abc/',
            published='',
        )
        message = format_message(1, post)

        self.assertLessEqual(len(message), 1000)
        self.assertIn('A' * 797, message)
        self.assertNotIn('A' * 798, message)
        self.assertIn(post.url, message)


if __name__ == '__main__':
    unittest.main()
