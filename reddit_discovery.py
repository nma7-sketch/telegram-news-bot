import asyncio
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from telegram import Bot


SUBREDDIT = 'todayilearned'
ATOM_NAMESPACE = '{http://www.w3.org/2005/Atom}'


@dataclass(frozen=True)
class RedditPost:
    title: str
    url: str
    published: str


def build_feed_url() -> str:
    query = urlencode({'t': 'day', 'limit': '30'})
    return f'https://www.reddit.com/r/{SUBREDDIT}/top/.rss?{query}'


def parse_feed(xml_data: bytes) -> tuple[RedditPost, ...]:
    root = ET.fromstring(xml_data)
    posts = []
    for entry in root.findall(f'{ATOM_NAMESPACE}entry'):
        title_element = entry.find(f'{ATOM_NAMESPACE}title')
        link_element = entry.find(f'{ATOM_NAMESPACE}link')
        published_element = entry.find(f'{ATOM_NAMESPACE}published')
        if title_element is None or link_element is None:
            continue

        title = (title_element.text or '').strip()
        url = (link_element.get('href') or '').strip()
        if not title or urlparse(url).hostname not in {'reddit.com', 'www.reddit.com'}:
            continue

        posts.append(
            RedditPost(
                title=title,
                url=url,
                published=(published_element.text or '').strip()
                if published_element is not None
                else '',
            )
        )

    return tuple(posts)


def fetch_top_posts() -> tuple[RedditPost, ...]:
    request = Request(
        build_feed_url(),
        headers={'User-Agent': 'telegram-news-bot/1.0 (read-only Reddit RSS client)'},
    )
    with urlopen(request, timeout=30) as response:
        posts = parse_feed(response.read())
    if not posts:
        raise RuntimeError(f'Reddit returned no posts from r/{SUBREDDIT}.')
    return posts


def select_post(
    posts: tuple[RedditPost, ...],
    at: datetime | None = None,
) -> tuple[int, RedditPost]:
    if not posts:
        raise ValueError('At least one Reddit post is required.')
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('The selection time must include a timezone.')
    two_hour_slot = int(moment.astimezone(timezone.utc).timestamp() // 7200)
    index = two_hour_slot % len(posts)
    return index + 1, posts[index]


def format_message(rank: int, post: RedditPost) -> str:
    title = post.title
    if len(title) > 800:
        title = title[:797].rstrip() + '...'
    return (
        f'🧠 Reddit Learning — r/{SUBREDDIT} (Top #{rank} today)\n\n'
        f'{title}\n\n'
        f'{post.url}'
    )


async def main() -> None:
    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
    channel_id = (os.getenv('CHANNEL_ID') or '').strip()
    if not bot_token or not channel_id:
        raise RuntimeError('TELEGRAM_BOT_TOKEN and CHANNEL_ID must both be configured.')

    rank, post = select_post(fetch_top_posts())
    async with Bot(token=bot_token) as bot:
        await bot.send_message(
            chat_id=channel_id,
            text=format_message(rank, post),
            disable_web_page_preview=True,
        )


if __name__ == '__main__':
    asyncio.run(main())
