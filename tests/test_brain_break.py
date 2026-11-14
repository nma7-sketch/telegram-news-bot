import unittest
from datetime import datetime, timedelta, timezone

from brain_break import BRAIN_BREAKS, BrainBreak, format_message, get_brain_break


class BrainBreakTests(unittest.TestCase):
    def test_questions_rotate_every_30_minutes_and_wrap(self):
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)

        self.assertEqual(get_brain_break(start), (1, BRAIN_BREAKS[0]))
        self.assertEqual(
            get_brain_break(start + timedelta(minutes=30)),
            (2, BRAIN_BREAKS[1]),
        )
        self.assertEqual(
            get_brain_break(start + timedelta(minutes=30 * len(BRAIN_BREAKS))),
            (1, BRAIN_BREAKS[0]),
        )

    def test_selection_is_timezone_independent(self):
        utc_time = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        local_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))

        self.assertEqual(get_brain_break(utc_time), get_brain_break(local_time))

    def test_naive_datetime_is_rejected(self):
        with self.assertRaises(ValueError):
            get_brain_break(datetime(2026, 1, 1))

    def test_deck_has_valid_choices_and_answers(self):
        for brain_break in BRAIN_BREAKS:
            with self.subTest(question=brain_break.question):
                self.assertEqual(len(brain_break.choices), 4)
                self.assertTrue(brain_break.answer.startswith(('A — ', 'B — ', 'C — ', 'D — ')))
                self.assertTrue(brain_break.explanation)

    def test_message_includes_all_choices_answer_and_explanation(self):
        brain_break = BrainBreak(
            category='Test',
            question='Which option is correct?',
            choices=('One', 'Two', 'Three', 'Four'),
            answer='B — Two',
            explanation='Two is correct.',
        )

        message = format_message(7, brain_break)

        for expected in ('#7', brain_break.question, *brain_break.choices, brain_break.answer, brain_break.explanation):
            self.assertIn(expected, message)


if __name__ == '__main__':
    unittest.main()
