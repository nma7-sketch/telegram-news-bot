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

The **30-Minute Market News** workflow sends a single digest every 30 minutes
(UTC), with one fresh public headline for each available publisher region. It
covers finance, stocks, oil, crypto, and currencies using RSS feeds from the
US, UK, India, Australia, Japan, Hong Kong, and global publications. Country
flags identify the publisher's region, not necessarily the event's location.
The workflow rejects items older than 24 hours and keeps seven days of
duplicate history in the GitHub Actions cache. It uses the existing Telegram
secrets and can be run manually from the Actions tab. It only uses public
reporting, including public disclosures when reported by those sources; it does
not seek or publish non-public insider information.

## Reddit Learning

The **Reddit Learning** workflow shares a rotating post from the daily top
feed in r/todayilearned with Telegram every two hours (UTC). It uses Reddit's
public RSS feed, so no Reddit credentials are needed; it can also be run
manually from the Actions tab.