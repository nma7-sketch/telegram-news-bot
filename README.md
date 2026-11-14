# telegram-news-bot

## Hourly Enlightenment

The **Hourly Enlightenment** GitHub Actions workflow sends a rotating, sourced
science or nature fact to the Telegram channel once an hour (UTC). It uses the
repository's `TELEGRAM_BOT_TOKEN` and `CHANNEL_ID` Actions secrets and can also
be run manually from the Actions tab.

## GitHub Project Discovery

The **GitHub Project Discovery** workflow queries GitHub's Search API for
repositories created in the current year, ordered by stars, and sends a rotating
repository spotlight to Telegram every two hours (UTC). It uses the built-in
GitHub Actions token plus the existing Telegram secrets and can also be run
manually from the Actions tab.

## 30-Minute Market News

The **30-Minute Market News** workflow shares recent public news about stocks,
finance, oil, crypto, and currencies every 30 minutes (UTC). It reads public
RSS headlines and links from outlets in the US, UK, India, Australia, and
Japan, Hong Kong, and global finance/crypto publications; the flag identifies
the outlet's country or global edition, not necessarily the event's location.
It rejects items older than 24 hours, rotates among regions, and keeps seven
days of duplicate history in the GitHub Actions cache. It uses the existing
Telegram secrets and can be run manually from the Actions tab. It only uses
public reporting, including public disclosures when reported by those sources;
it does not seek or publish non-public insider information.

## Reddit Learning

The **Reddit Learning** workflow shares a rotating post from the daily top
feed in r/todayilearned with Telegram every two hours (UTC). It uses Reddit's
public RSS feed, so no Reddit credentials are needed; it can also be run
manually from the Actions tab.