import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from github_discovery import (
    Repository,
    build_search_url,
    format_message,
    select_spotlight,
)


class GitHubDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.repositories = tuple(
            Repository(
                full_name=f'owner/project-{index}',
                description=f'Description {index}',
                url=f'https://github.com/owner/project-{index}',
                stars=100 - index,
                language='Python',
                created_at='2026-01-01',
            )
            for index in range(3)
        )

    def test_search_targets_this_year_and_orders_by_stars(self):
        url = build_search_url(datetime(2026, 11, 14, tzinfo=timezone.utc))
        query = parse_qs(urlparse(url).query)

        self.assertEqual(
            query['q'],
            ['created:2026-01-01..2026-11-14'],
        )
        self.assertEqual(query['sort'], ['stars'])
        self.assertEqual(query['order'], ['desc'])
        self.assertEqual(query['per_page'], ['30'])

    def test_spotlight_rotates_every_two_hours_and_wraps(self):
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)

        self.assertEqual(select_spotlight(self.repositories, start), (1, self.repositories[0]))
        self.assertEqual(
            select_spotlight(self.repositories, start + timedelta(hours=2)),
            (2, self.repositories[1]),
        )
        self.assertEqual(
            select_spotlight(self.repositories, start + timedelta(hours=6)),
            (1, self.repositories[0]),
        )

    def test_selection_is_timezone_independent(self):
        utc_time = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        local_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))

        self.assertEqual(
            select_spotlight(self.repositories, utc_time),
            select_spotlight(self.repositories, local_time),
        )

    def test_empty_results_and_naive_time_are_rejected(self):
        with self.assertRaises(ValueError):
            select_spotlight(())
        with self.assertRaises(ValueError):
            build_search_url(datetime(2026, 1, 1))

    def test_message_includes_repository_details(self):
        repository = self.repositories[0]
        message = format_message(1, repository)

        self.assertIn(repository.full_name, message)
        self.assertIn('100', message)
        self.assertIn(repository.description, message)
        self.assertIn(repository.url, message)


if __name__ == '__main__':
    unittest.main()
