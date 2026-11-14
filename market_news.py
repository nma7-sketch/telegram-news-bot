import asyncio
import hashlib
import html
import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from telegram import Bot


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

STATE_PATH = Path(os.getenv('MARKET_NEWS_STATE_PATH', '.market_news_state.json'))
MAX_AGE = timedelta(hours=24)
SEEN_RETENTION = timedelta(days=7)
FUTURE_TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class NewsFeed:
    name: str
    country_code: str
    country_name: str
    flag: str
    url: str


@dataclass(frozen=True)
class MarketArticle:
    title: str
    url: str
    published_at: datetime
    source: str
    country_code: str
    country_name: str
    flag: str
    category: str


FEEDS = (
    NewsFeed(
        'BBC Business', 'GB', 'UK', '🇬🇧',
        'https://feeds.bbci.co.uk/news/business/rss.xml',
    ),
    NewsFeed(
        'The Guardian Business', 'GB', 'UK', '🇬🇧',
        'https://www.theguardian.com/business/rss',
    ),
    NewsFeed(
        'CNBC Markets', 'US', 'US', '🇺🇸',
        'https://www.cnbc.com/id/10000664/device/rss/rss.html',
    ),
    NewsFeed(
        'WSJ Markets', 'US', 'US', '🇺🇸',
        'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
    ),
    NewsFeed(
        'Bloomberg Markets', 'US', 'US', '🇺🇸',
        'https://feeds.bloomberg.com/markets/news.rss',
    ),
    NewsFeed(
        'Economic Times Markets', 'IN', 'India', '🇮🇳',
        'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    ),
    NewsFeed(
        'ABC News Business', 'AU', 'Australia', '🇦🇺',
        'https://www.abc.net.au/news/feed/51120/rss.xml',
    ),
    NewsFeed(
        'Nikkei Asia', 'JP', 'Japan', '🇯🇵',
        'https://asia.nikkei.com/rss/feed/nar',
    ),
    NewsFeed(
        'SCMP Business', 'HK', 'Hong Kong', '🇭🇰',
        'https://www.scmp.com/rss/4/feed',
    ),
    NewsFeed(
        'OilPrice', 'GLOBAL', 'Global', '🌍',
        'https://oilprice.com/rss/main',
    ),
    NewsFeed(
        'Cointelegraph', 'GLOBAL', 'Global', '🌍',
        'https://cointelegraph.com/rss',
    ),
)

REGION_ORDER = ('GB', 'IN', 'AU', 'JP', 'HK', 'US', 'GLOBAL')
CATEGORY_PATTERNS = (
    (
        'Crypto',
        re.compile(
            r'\b(crypto(?:currency)?|bitcoin|btc|ethereum|ether|blockchain|stablecoin|digital assets?)\b',
            re.I,
        ),
    ),
    (
        'Oil',
        re.compile(
            r'\b(brent|wti|opec|petroleum|crude(?: oil)?|oil (?:markets?|prices?|output|production|supply|demand|trading|exports?|imports?|futures?|surges?|rises?|falls?|climbs?|drops?|spikes?))\b',
            re.I,
        ),
    ),
    (
        'Currency',
        re.compile(
            r'\b(forex|fx|foreign exchange|currenc(?:y|ies)|exchange rates?|usd(?:/[a-z]{3})?|eur(?:/[a-z]{3})?|jpy(?:/[a-z]{3})?|cny|inr|gbp|dollar (?:index|rises?|falls?|gains?|weakens?|strengthens?|slides?|surges?|drops?)|euro (?:rises?|falls?|gains?|weakens?|strengthens?|slides?|surges?|drops?)|yen (?:rises?|falls?|gains?|weakens?|strengthens?|slides?|surges?|drops?)|yuan (?:rises?|falls?|gains?|weakens?|strengthens?|slides?|surges?|drops?)|rupee (?:rises?|falls?|gains?|weakens?|strengthens?|slides?|surges?|drops?)|pound sterling|franc (?:rises?|falls?|gains?|weakens?|strengthens?|slides?|surges?|drops?))\b',
            re.I,
        ),
    ),
    (
        'Stocks',
        re.compile(
            r'\b(stocks?|equities|equity|nasdaq|nyse|s&p 500|dow jones|ftse|nikkei|nifty|sensex|ipo|bond yields?|treasury yields?|share prices?|shares? (?:rise|rises|rose|fall|falls|fell|gain|gains|climb|climbs|slide|slides|jump|jumps|surge|surges|drop|drops|soar|soars|trade|trading|edge|close|close higher|close lower))\b',
            re.I,
        ),
    ),
    (
        'Finance',
        re.compile(
            r'\b(finance|financial|banking|central banks?|interest rates?|rate cuts?|rate hikes?|inflation|earnings|federal reserve|ecb|bank of england|boj|insider trading|insider trades?|insider buying|insider selling|insider transactions?|form 4 filings?)\b',
            re.I,
        ),
    ),
)
CATEGORY_ICONS = {
    'Crypto': '₿',
    'Oil': '🛢',
    'Currency': '💱',
    'Stocks': '📈',
    'Finance': '💰',
}


def classify_title(title: str) -> str | None:
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(title):
            return category
    return None


def _element_text(element: ET.Element, *names: str) -> str:
    for child in element:
        if child.tag.rsplit('}', 1)[-1].lower() in names:
            return ''.join(child.itertext()).strip()
    return ''


def _element_link(element: ET.Element) -> str:
    for child in element:
        if child.tag.rsplit('}', 1)[-1].lower() != 'link':
            continue
        href = child.attrib.get('href')
        if href and child.attrib.get('rel', 'alternate') == 'alternate':
            return href.strip()
        if child.text and child.text.strip():
            return child.text.strip()
    return ''


def _parse_published_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        published = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            published = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    if published.tzinfo is None or published.utcoffset() is None:
        published = published.replace(tzinfo=timezone.utc)
    return published.astimezone(timezone.utc)


def parse_feed(
    xml_data: bytes,
    feed: NewsFeed,
    now: datetime | None = None,
) -> tuple[MarketArticle, ...]:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('The parsing time must include a timezone.')
    moment = moment.astimezone(timezone.utc)
    root = ET.fromstring(xml_data)
    articles = []

    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1].lower() not in {'item', 'entry'}:
            continue
        title = html.unescape(_element_text(element, 'title')).strip()
        url = _element_link(element)
        published_value = _element_text(element, 'pubdate', 'published', 'updated', 'date')
        published_at = _parse_published_date(published_value)
        parsed_url = urlparse(url)
        category = classify_title(title)

        if (
            not title
            or parsed_url.scheme != 'https'
            or not parsed_url.netloc
            or published_at is None
            or moment - published_at > MAX_AGE
            or published_at - moment > FUTURE_TOLERANCE
            or category is None
        ):
            continue

        source = _element_text(element, 'source') or feed.name
        articles.append(
            MarketArticle(
                title=title,
                url=url,
                published_at=published_at,
                source=source,
                country_code=feed.country_code,
                country_name=feed.country_name,
                flag=feed.flag,
                category=category,
            )
        )

    return tuple(articles)


def fetch_recent_news(
    feeds: tuple[NewsFeed, ...] = FEEDS,
    now: datetime | None = None,
) -> tuple[MarketArticle, ...]:
    articles = []
    successful_feeds = 0
    for feed in feeds:
        request = Request(
            feed.url,
            headers={'User-Agent': 'telegram-news-bot/1.0 (public RSS headlines and links)'},
        )
        try:
            with urlopen(request, timeout=20) as response:
                feed_articles = parse_feed(response.read(), feed, now)
        except (OSError, ET.ParseError, UnicodeDecodeError) as error:
            logger.warning('Could not read %s: %s', feed.name, error)
            continue
        successful_feeds += 1
        articles.extend(feed_articles)

    if not successful_feeds:
        raise RuntimeError('All public market-news feeds failed; no news was sent.')
    return tuple(articles)


def _fingerprints(article: MarketArticle) -> tuple[str, str]:
    normalized_title = re.sub(r'\W+', '', article.title.casefold())
    normalized_url = f'{urlparse(article.url).netloc.lower()}{urlparse(article.url).path.rstrip("/")}'
    title_hash = hashlib.sha256(normalized_title.encode('utf-8')).hexdigest()
    url_hash = hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
    return f'title:{title_hash}', f'url:{url_hash}'


def load_state(path: Path = STATE_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding='utf-8') as state_file:
        state = json.load(state_file)
    if not isinstance(state, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in state.items()
    ):
        raise ValueError('Market-news history has an invalid format.')
    return state


def save_state(state: dict[str, str], path: Path = STATE_PATH) -> None:
    temporary_path = path.with_suffix(path.suffix + '.tmp')
    with temporary_path.open('w', encoding='utf-8') as state_file:
        json.dump(state, state_file, sort_keys=True)
    temporary_path.replace(path)


def remove_old_history(
    state: dict[str, str],
    now: datetime,
) -> dict[str, str]:
    moment = now.astimezone(timezone.utc)
    cutoff = moment - SEEN_RETENTION
    recent = {}
    for fingerprint, timestamp in state.items():
        try:
            seen_at = datetime.fromisoformat(timestamp)
        except ValueError:
            continue
        if seen_at.tzinfo is None or seen_at.utcoffset() is None:
            seen_at = seen_at.replace(tzinfo=timezone.utc)
        if seen_at.astimezone(timezone.utc) >= cutoff:
            recent[fingerprint] = timestamp
    return recent


def select_articles(
    articles: tuple[MarketArticle, ...],
    state: dict[str, str],
) -> tuple[MarketArticle, ...]:
    selected: list[MarketArticle] = []
    selected_fingerprints: set[str] = set()
    for region in REGION_ORDER:
        unseen = [
            article
            for article in articles
            if article.country_code == region
            and not any(fingerprint in state for fingerprint in _fingerprints(article))
            and not any(
                fingerprint in selected_fingerprints
                for fingerprint in _fingerprints(article)
            )
        ]
        if unseen:
            article = max(unseen, key=lambda item: item.published_at)
            selected.append(article)
            selected_fingerprints.update(_fingerprints(article))
    return tuple(selected)


def format_digest(
    articles: tuple[MarketArticle, ...],
    now: datetime | None = None,
) -> tuple[str, ...]:
    if not articles:
        return ()
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('The digest time must include a timezone.')
    moment = moment.astimezone(timezone.utc)
    header = (
        f'🌍 Global Market Briefing · {moment.strftime("%Y-%m-%d %H:%M UTC")}\n'
        'Fresh public headlines from each available region:\n\n'
    )
    sections = []
    for article in articles:
        age = moment - article.published_at
        if age < timedelta(minutes=1):
            age_text = 'just now'
        elif age < timedelta(hours=1):
            age_text = f'{int(age.total_seconds() // 60)} min ago'
        else:
            age_text = f'{int(age.total_seconds() // 3600)} hr ago'
        icon = CATEGORY_ICONS[article.category]
        title = article.title
        if len(title) > 200:
            title = title[:197].rstrip() + '...'
        sections.append(
            f'{article.flag} {article.country_name} source · '
            f'{icon} {article.category.upper()} · {age_text}\n'
            f'{title}\n'
            f'{article.source}\n'
            f'{article.url}'
        )

    messages = []
    current = header
    for section in sections:
        addition = f'{section}\n\n'
        if len(current) + len(addition) > 3900 and current != header:
            messages.append(current.rstrip())
            current = f'{header}(continued)\n\n'
        if len(current) + len(addition) > 3900:
            raise ValueError('A market-news item exceeds Telegram message limits.')
        current += addition
    current += 'Public reporting only · Not investment advice'
    if len(current) > 4096:
        raise ValueError('The market-news digest exceeds Telegram message limits.')
    messages.append(current)
    return tuple(messages)


async def main() -> None:
    bot_token = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
    channel_id = (os.getenv('CHANNEL_ID') or '').strip()
    if not bot_token or not channel_id:
        raise RuntimeError('TELEGRAM_BOT_TOKEN and CHANNEL_ID must both be configured.')

    now = datetime.now(timezone.utc)
    state = remove_old_history(load_state(), now)
    articles = fetch_recent_news(now=now)
    selected = select_articles(articles, state)
    if not selected:
        logger.info('No fresh, unseen market headlines found; nothing was sent.')
        save_state(state)
        return

    messages = format_digest(selected, now)
    async with Bot(token=bot_token) as bot:
        for message in messages:
            await bot.send_message(
                chat_id=channel_id,
                text=message,
                disable_web_page_preview=True,
            )

    for article in selected:
        for fingerprint in _fingerprints(article):
            state[fingerprint] = now.isoformat()
    save_state(state)
    logger.info('Sent %d market headlines across %d Telegram message(s).', len(selected), len(messages))


if __name__ == '__main__':
    asyncio.run(main())
