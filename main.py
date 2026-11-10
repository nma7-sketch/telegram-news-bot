import os
import json
import logging
from telegram import Bot
import asyncio
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get credentials from environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

class NewsBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.posted_links_file = 'posted_links.json'
        self.load_posted_links()
    
    def load_posted_links(self):
        """Load already posted links"""
        try:
            with open(self.posted_links_file, 'r') as f:
                self.posted_links = json.load(f)
                logger.info(f"Loaded {len(self.posted_links)} posted links")
        except FileNotFoundError:
            self.posted_links = []
            logger.info("No posted links file found, starting fresh")
    
    def save_posted_links(self):
        """Save posted links to file"""
        with open(self.posted_links_file, 'w') as f:
            json.dump(self.posted_links, f, indent=2)
        logger.info("Saved posted links")
    
    async def send_test_message(self):
        """Send a test message to verify bot works"""
        try:
            await self.bot.send_message(
                chat_id=CHANNEL_ID,
                text=" *Bot is Online!*\n\n✅ Connection successful!\n🕐 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                parse_mode='Markdown'
            )
            logger.info("✅ Test message sent successfully!")
            return True
        except Exception as e:
            logger.error(f" Failed to send test message: {e}")
            return False
    
    async def send_news(self, title, description, link):
        """Send news to channel"""
        try:
            message = f"📰 *{title}*\n\n"
            message += f"{description}\n\n"
            message += f"🔗 [Read More]({link})"
            
            await self.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            logger.info(f"✅ Posted: {title}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to post {title}: {e}")
            return False

async def main():
    """Main function"""
    logger.info("🚀 Starting Telegram News Bot...")
    
    # Check credentials
    if not BOT_TOKEN:
        logger.error(" BOT_TOKEN not found in environment variables!")
        return
    
    if not CHANNEL_ID:
        logger.error("❌ CHANNEL_ID not found in environment variables!")
        return
    
    logger.info(f"📱 Bot Token: {BOT_TOKEN[:10]}...")
    logger.info(f"📢 Channel ID: {CHANNEL_ID}")
    
    # Initialize bot
    bot = NewsBot()
    
    # Send test message
    test_sent = await bot.send_test_message()
    
    if not test_sent:
        logger.error("❌ Test message failed. Check your BOT_TOKEN and CHANNEL_ID")
        return
    
    # Example: Send sample news (Replace this with your actual news scraping logic)
    sample_news = [
        {
            "title": "Welcome to Your News Bot!",
            "description": "This is your first automated news post. Configure your bot to fetch real news from RSS feeds or APIs.",
            "link": "https://github.com"
        }
    ]
    
    for news in sample_news:
        link = news['link']
        if link not in bot.posted_links:
            await bot.send_news(news['title'], news['description'], link)
            bot.posted_links.append(link)
    
    # Save posted links
    bot.save_posted_links()
    
    logger.info("✅ Bot finished successfully!")

if __name__ == '__main__':
    asyncio.run(main())
