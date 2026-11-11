# telegram-news-bot

## Telegram channel setup

Add the bot to the channel as an administrator and allow it to post messages.
Store `TELEGRAM_BOT_TOKEN` and `CHANNEL_ID` as GitHub Actions repository secrets.

For a public channel, `CHANNEL_ID` can be its `@username`. For a private channel,
set it to the channel's numeric chat ID (typically starts with `-100`, with no
`@`). The bot converts numeric IDs before sending the report. Keep the bot token
private.

The workflow can be run manually and is scheduled to run every four hours.