import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from telegram import Bot


@dataclass(frozen=True)
class Curiosity:
    topic: str
    fact: str
    source: str


CURIOSITIES = (
    Curiosity(
        'Venus',
        'A Venusian sidereal day (one rotation) lasts about 243 Earth days—longer than its 225-day year.',
        'https://science.nasa.gov/venus/venus-facts/',
    ),
    Curiosity(
        'The Moon',
        'The Moon is slowly moving away from Earth by about 3.8 centimetres each year.',
        'https://science.nasa.gov/moon/facts/',
    ),
    Curiosity(
        'Saturn',
        'Saturn is less dense than water on average. There is no ocean large enough to float it, though!',
        'https://science.nasa.gov/saturn/facts/',
    ),
    Curiosity(
        'Mercury',
        'Mercury rotates three times for every two orbits around the Sun—a 3:2 spin-orbit resonance.',
        'https://science.nasa.gov/mercury/facts/',
    ),
    Curiosity(
        'Jupiter',
        'Jupiter completes a rotation in roughly 10 hours, giving it the shortest day of any planet in our solar system.',
        'https://science.nasa.gov/jupiter/facts/',
    ),
    Curiosity(
        'Sunlight',
        'Sunlight takes about 8 minutes and 20 seconds to travel from the Sun to Earth.',
        'https://science.nasa.gov/sun/facts/',
    ),
    Curiosity(
        'Earth’s air',
        'Earth’s dry atmosphere is about 78% nitrogen and 21% oxygen by volume.',
        'https://www.noaa.gov/jetstream/atmosphere',
    ),
    Curiosity(
        'Tectonic plates',
        'Earth’s outer shell is broken into moving plates; their interactions cause most earthquakes and volcanoes.',
        'https://www.usgs.gov/programs/earthquake-hazards/science/tectonic-plates',
    ),
    Curiosity(
        'Lightning',
        'A lightning channel can heat the surrounding air to around 50,000°F—hotter than the Sun’s visible surface.',
        'https://www.nssl.noaa.gov/education/svrwx101/lightning/',
    ),
    Curiosity(
        'Ocean sound',
        'Sound travels roughly four times faster in seawater than in air, helping whales communicate over long distances.',
        'https://oceanservice.noaa.gov/facts/sound.html',
    ),
    Curiosity(
        'The International Space Station',
        'The ISS travels around Earth at about 28,000 kilometres per hour, completing an orbit in roughly 90 minutes.',
        'https://www.nasa.gov/international-space-station/space-station-facts-and-figures/',
    ),
    Curiosity(
        'CRISPR',
        'CRISPR-Cas9 gene editing was adapted from a defence system bacteria use against viruses.',
        'https://www.genome.gov/about-genomics/fact-sheets/CRISPR-Cas9-Fact-Sheet',
    ),
    Curiosity(
        'The human genome',
        'A human genome contains about 3 billion DNA base pairs, packed into nearly every cell.',
        'https://www.genome.gov/about-genomics/fact-sheets/Genomics-Facts-Fact-Sheet',
    ),
    Curiosity(
        'Bananas',
        'In botanical terms, bananas are berries; strawberries are not true berries.',
        'https://www.britannica.com/story/is-a-banana-a-fruit-or-a-berry',
    ),
    Curiosity(
        'Flamingos',
        'Flamingos get their pink colour from carotenoid pigments in the algae and tiny crustaceans they eat.',
        'https://nationalzoo.si.edu/animals/flamingo',
    ),
    Curiosity(
        'Water',
        'Fresh water is densest at about 4°C. As it cools further, it becomes less dense, which is why ice floats.',
        'https://www.usgs.gov/special-topics/water-science-school/science/water-density',
    ),
)


def get_hourly_curiosity(at: datetime | None = None) -> Curiosity:
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('The selection time must include a timezone.')
    hour_index = int(moment.astimezone(timezone.utc).timestamp() // 3600)
    return CURIOSITIES[hour_index % len(CURIOSITIES)]


def format_message(curiosity: Curiosity) -> str:
    return (
        f'💡 Hourly Enlightenment — {curiosity.topic}\n\n'
        f'{curiosity.fact}\n\n'
        f'Source: {curiosity.source}'
    )


async def main() -> None:
    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
    channel_id = (os.getenv('CHANNEL_ID') or '').strip()
    if not bot_token or not channel_id:
        raise RuntimeError('TELEGRAM_BOT_TOKEN and CHANNEL_ID must both be configured.')

    curiosity = get_hourly_curiosity()
    async with Bot(token=bot_token) as bot:
        await bot.send_message(
            chat_id=channel_id,
            text=format_message(curiosity),
            disable_web_page_preview=True,
        )


if __name__ == '__main__':
    asyncio.run(main())
