import unittest
from datetime import datetime, timedelta, timezone

from hourly_enlightenment import CURIOSITIES, format_message, get_hourly_curiosity


class HourlyEnlightenmentTests(unittest.TestCase):
    def test_curiosity_advances_each_hour_and_wraps(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)

        self.assertEqual(get_hourly_curiosity(start), CURIOSITIES[0])
        self.assertEqual(get_hourly_curiosity(start + timedelta(hours=1)), CURIOSITIES[1])
        self.assertEqual(
            get_hourly_curiosity(start + timedelta(hours=len(CURIOSITIES))),
            CURIOSITIES[0],
        )

    def test_selection_is_independent_of_timezone(self):
        utc_time = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        local_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))

        self.assertEqual(get_hourly_curiosity(utc_time), get_hourly_curiosity(local_time))

    def test_naive_datetime_is_rejected(self):
        with self.assertRaises(ValueError):
            get_hourly_curiosity(datetime(2026, 1, 1))

    def test_message_includes_fact_and_source(self):
        curiosity = CURIOSITIES[0]
        message = format_message(curiosity)

        self.assertIn(curiosity.topic, message)
        self.assertIn(curiosity.fact, message)
        self.assertIn(curiosity.source, message)


if __name__ == '__main__':
    unittest.main()
