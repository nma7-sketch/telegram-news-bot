import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from telegram import Bot


@dataclass(frozen=True)
class BrainBreak:
    category: str
    question: str
    choices: tuple[str, str, str, str]
    answer: str
    explanation: str


BRAIN_BREAKS = (
    BrainBreak(
        'Quick math',
        'A bat and a ball cost $1.10 together. The bat costs $1 more than the ball. How much is the ball?',
        ('$0.05', '$0.10', '$0.15', '$0.20'),
        'A — $0.05',
        'Then the bat is $1.05, making the total $1.10.',
    ),
    BrainBreak(
        'Think carefully',
        'You pass the runner in second place during a race. What place are you in now?',
        ('First', 'Second', 'Third', 'It depends on the finish line'),
        'B — Second',
        'You take the place of the runner you passed; the first-place runner is still ahead.',
    ),
    BrainBreak(
        'Pattern spotting',
        'What number comes next: 1, 1, 2, 3, 5, 8, __?',
        ('11', '12', '13', '15'),
        'C — 13',
        'Each number is the sum of the two before it: 5 + 8 = 13.',
    ),
    BrainBreak(
        'A classic puzzle',
        'A clock takes 5 seconds to strike 6 times. How long does it take to strike 12 times?',
        ('10 seconds', '11 seconds', '12 seconds', '15 seconds'),
        'B — 11 seconds',
        'Six strikes have five gaps. Twelve strikes have eleven gaps, each one second long.',
    ),
    BrainBreak(
        'Everyday logic',
        'A drawer has black and blue socks, all mixed together. What is the fewest you must take in the dark to guarantee a matching-colour pair?',
        ('2', '3', '4', '5'),
        'B — 3',
        'With only two colours, three socks must include at least two of one colour.',
    ),
    BrainBreak(
        'Machines at work',
        'If 5 machines make 5 widgets in 5 minutes, how long would 100 identical machines take to make 100 widgets?',
        ('5 minutes', '20 minutes', '100 minutes', '500 minutes'),
        'A — 5 minutes',
        'Each machine makes one widget in five minutes, so 100 machines make 100 in parallel.',
    ),
    BrainBreak(
        'Wordplay',
        'How many months have at least 28 days?',
        ('1', '2', '11', '12'),
        'D — 12',
        'Every month has at least 28 days.',
    ),
    BrainBreak(
        'Family puzzle',
        'Two fathers and two sons go fishing. They catch three fish, and each person gets one. How is that possible?',
        ('One fish was shared', 'There were only three people', 'One person got two fish', 'There were four people but one fish was extra'),
        'B — There were only three people',
        'They are a grandfather, his son, and his grandson: two fathers and two sons.',
    ),
    BrainBreak(
        'Quick comparison',
        'Which is heavier: a kilogram of feathers or a kilogram of steel?',
        ('The feathers', 'The steel', 'They weigh the same', 'It depends on the container'),
        'C — They weigh the same',
        'Both have a mass of one kilogram.',
    ),
    BrainBreak(
        'A little strategy',
        'There are 8 identical-looking balls; one is heavier. What is the fewest balance-scale weighings needed to guarantee finding it?',
        ('1', '2', '3', '4'),
        'B — 2',
        'Weigh 3 against 3. If equal, compare the last two; otherwise, weigh two from the heavier group against each other.',
    ),
    BrainBreak(
        'Lily pond',
        'A patch of lily pads doubles in area every day. It covers the whole pond on day 48. When did it cover half?',
        ('Day 24', 'Day 46', 'Day 47', 'Day 48'),
        'C — Day 47',
        'One day before it doubles to cover the entire pond, it covers half.',
    ),
    BrainBreak(
        'Electricity',
        'You are outside watching an electric train travel north. The wind blows south. Which way does the smoke go?',
        ('North', 'South', 'Up', 'There is no smoke'),
        'D — There is no smoke',
        'It is an electric train.',
    ),
    BrainBreak(
        'A final twist',
        'A farmer has 17 sheep. All but 9 wander away. How many are left?',
        ('8', '9', '17', 'None'),
        'B — 9',
        '“All but 9” means 9 sheep remain.',
    ),
    BrainBreak(
        'Time puzzle',
        'You take 3 pills, one every 30 minutes. How long from the first pill until you take the last?',
        ('30 minutes', '1 hour', '1.5 hours', '2 hours'),
        'B — 1 hour',
        'Take the first now, the second after 30 minutes, and the third after 60 minutes.',
    ),
    BrainBreak(
        'Count it',
        'You take 2 apples from a basket of 3. How many apples do you have?',
        ('1', '2', '3', '5'),
        'B — 2',
        'You took two apples, so you have two.',
    ),
    BrainBreak(
        'One more pattern',
        'What comes next: 2, 6, 12, 20, 30, __?',
        ('36', '40', '42', '48'),
        'C — 42',
        'The differences are 4, 6, 8, 10; the next difference is 12.',
    ),
)


def get_brain_break(at: datetime | None = None) -> tuple[int, BrainBreak]:
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('The selection time must include a timezone.')
    half_hour_slot = int(moment.astimezone(timezone.utc).timestamp() // 1800)
    index = half_hour_slot % len(BRAIN_BREAKS)
    return index + 1, BRAIN_BREAKS[index]


def format_message(number: int, brain_break: BrainBreak) -> str:
    choices = '\n'.join(
        f'{letter}. {choice}'
        for letter, choice in zip('ABCD', brain_break.choices)
    )
    return (
        f'🧠 30-Minute Brain Break — #{number}: {brain_break.category}\n\n'
        f'{brain_break.question}\n\n'
        f'{choices}\n\n'
        f'✅ Answer: {brain_break.answer}\n'
        f'{brain_break.explanation}'
    )


async def main() -> None:
    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
    channel_id = (os.getenv('CHANNEL_ID') or '').strip()
    if not bot_token or not channel_id:
        raise RuntimeError('TELEGRAM_BOT_TOKEN and CHANNEL_ID must both be configured.')

    number, brain_break = get_brain_break()
    async with Bot(token=bot_token) as bot:
        await bot.send_message(
            chat_id=channel_id,
            text=format_message(number, brain_break),
            disable_web_page_preview=True,
        )


if __name__ == '__main__':
    asyncio.run(main())
