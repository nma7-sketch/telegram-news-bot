import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from telegram import Bot


@dataclass(frozen=True)
class Repository:
    full_name: str
    description: str
    url: str
    stars: int
    language: str
    created_at: str


def build_search_url(at: datetime | None = None) -> str:
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('The search date must include a timezone.')
    today = moment.astimezone(timezone.utc).date()
    query = {
        'q': f'created:{today.year}-01-01..{today.isoformat()}',
        'sort': 'stars',
        'order': 'desc',
        'per_page': '30',
    }
    return f'https://api.github.com/search/repositories?{urlencode(query)}'


def fetch_top_repositories(token: str, at: datetime | None = None) -> tuple[Repository, ...]:
    request = Request(
        build_search_url(at),
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {token}',
            'User-Agent': 'telegram-news-bot',
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    items = payload.get('items')
    if not isinstance(items, list) or not items:
        raise RuntimeError('GitHub returned no repositories for the current year.')

    return tuple(
        Repository(
            full_name=item['full_name'],
            description=item.get('description') or 'No description provided.',
            url=item['html_url'],
            stars=item['stargazers_count'],
            language=item.get('language') or 'Not specified',
            created_at=item['created_at'][:10],
        )
        for item in items
    )


def select_spotlight(
    repositories: tuple[Repository, ...],
    at: datetime | None = None,
) -> tuple[int, Repository]:
    if not repositories:
        raise ValueError('At least one repository is required.')
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('The selection time must include a timezone.')
    two_hour_slot = int(moment.astimezone(timezone.utc).timestamp() // 7200)
    index = two_hour_slot % len(repositories)
    return index + 1, repositories[index]


def format_message(rank: int, repository: Repository) -> str:
    year = repository.created_at[:4]
    return (
        f'🔎 GitHub {year} Discovery — #{rank} by stars\n\n'
        f'{repository.full_name} ⭐ {repository.stars:,}\n'
        f'{repository.description}\n\n'
        f'Language: {repository.language}\n'
        f'Created: {repository.created_at}\n'
        f'{repository.url}\n\n'
        f'Source: GitHub repository search, created in {year} and sorted by stars.'
    )


async def main() -> None:
    github_token = (os.getenv('GH_TOKEN') or '').strip()
    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
    channel_id = (os.getenv('CHANNEL_ID') or '').strip()
    if not github_token or not bot_token or not channel_id:
        raise RuntimeError('GH_TOKEN, TELEGRAM_BOT_TOKEN, and CHANNEL_ID must be configured.')

    repositories = fetch_top_repositories(github_token)
    rank, repository = select_spotlight(repositories)
    async with Bot(token=bot_token) as bot:
        await bot.send_message(
            chat_id=channel_id,
            text=format_message(rank, repository),
            disable_web_page_preview=True,
        )


if __name__ == '__main__':
    asyncio.run(main())
