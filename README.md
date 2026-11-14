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