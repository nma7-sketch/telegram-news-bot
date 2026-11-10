import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import tempfile
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# Define our Wall Street Sources
TARGET_SOURCES = {
    "Jane Street": "https://www.janestreet.com/insights/",
    "AQR Capital": "https://www.aqr.com/Insights",
    "Bridgewater": "https://www.bridgewater.com/research-and-insights",
    "BlackRock": "https://www.blackrock.com/us/individual/insights",
    "Citadel Securities": "https://www.citadelsecurities.com/insights/"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

class WallStreetBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.posted_links_file = 'posted_links.json'
        self.load_posted_links()
    
    def load_posted_links(self):
        try:
            with open(self.posted_links_file, 'r') as f:
                self.posted_links = json.load(f)
        except FileNotFoundError:
            self.posted_links = []

    def save_posted_links(self):
        with open(self.posted_links_file, 'w') as f:
            json.dump(self.posted_links, f, indent=2)

    def is_relevant_resource(self, text, href):
        """Filter out navigation links and only keep real research/PDFs/Videos"""
        text_lower = text.lower()
        href_lower = href.lower()
        
        # 1. Direct file links
        if href_lower.endswith('.pdf') or href_lower.endswith('.mp4'):
            return True
            
        # 2. Keywords indicating a real research paper, video, or report
        keywords = ['research', 'insight', 'report', 'outlook', 'video', 'whitepaper', 'guide', 'market']
        
        # Must have a keyword in the text or URL, and be long enough to be a title
        if len(text) > 15 and any(k in text_lower or k in href_lower for k in keywords):
            return True
            
        return False

    def scrape_all_sources(self):
        """Scrape PDFs and Videos from all Wall Street sources"""
        all_resources = []
        
        for source_name, url in TARGET_SOURCES.items():
            logger.info(f"🕵️ Scraping {source_name}...")
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                found_count = 0
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    text = a_tag.get_text(strip=True)
                    
                    # Resolve relative URLs
                    full_url = urljoin(url, href)
                    
                    # Ensure it's an external link to a resource, not an internal nav link
                    if self.is_relevant_resource(text, full_url):
                        # Avoid duplicates within the same page
                        if not any(r['link'] == full_url for r in all_resources):
                            all_resources.append({
                                "title": text,
                                "link": full_url,
                                "source": source_name
                            })
                            found_count += 1
                            
                logger.info(f"✅ Found {found_count} resources from {source_name}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to scrape {source_name}: {e}")
            
            # Be polite to servers
            asyncio.sleep(2) 
            
        logger.info(f"📊 Total unique resources found: {len(all_resources)}")
        return all_resources

    async def download_and_upload_pdf(self, pdf_url, title, source):
        """Download PDF and upload directly to Telegram"""
        try:
            response = requests.get(pdf_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            file_size_mb = len(response.content) / (1024 * 1024)
            if file_size_mb > 50:
                logger.warning(f"⚠️ PDF too large ({file_size_mb:.2f} MB): {title}")
                return False
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            caption = f"🏦 <b>Source: {source}</b>\n\n📂 <b>{title}</b>"
            
            with open(tmp_path, 'rb') as pdf_file:
                await self.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=pdf_file,
                    caption=caption,
                    parse_mode='HTML'
                )
            
            os.unlink(tmp_path)
            return True
            
        except Exception as e:
            logger.error(f"❌ PDF Upload failed for {title}: {e}")
            return False

    async def send_resource(self, item):
        """Send resource - upload PDFs directly, send videos/other as links"""
        title = item['title']
        link = item['link']
        source = item['source']
        
        if link.lower().endswith('.pdf'):
            success = await self.download_and_upload_pdf(link, title, source)
            if not success:
                return await self.send_as_link(title, link, source)
            return success
        else:
            return await self.send_as_link(title, link, source)

    async def send_as_link(self, title, link, source):
        """Send resource as a clickable link"""
        try:
            message = f"🏦 <b>Source: {source}</b>\n\n"
            message += f"📂 <b>{title}</b>\n\n"
            message += f"🔗 <a href='{link}'>Access Resource</a>"
            
            await self.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            return True
        except Exception as e:
            logger.error(f"❌ Link post failed: {e}")
            return False

async def main():
    logger.info("=" * 50)
    logger.info("🚀 STARTING WALL STREET MULTI-SOURCE BOT")
    logger.info("=" * 50)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("❌ Missing BOT_TOKEN or CHANNEL_ID!")
        return
    
    bot = WallStreetBot()
    resources = bot.scrape_all_sources()
    
    new_posts_count = 0
    for item in resources:
        if item['link'] not in bot.posted_links:
            success = await bot.send_resource(item)
            if success:
                bot.posted_links.append(item['link'])
                new_posts_count += 1
                await asyncio.sleep(3) # Prevent rate limiting
    
    if new_posts_count > 0:
        bot.save_posted_links()
        logger.info(f"✅ Successfully posted {new_posts_count} new Wall Street resources!")
    else:
        logger.info("ℹ️ No new resources to post.")
    
    logger.info("=" * 50)
    logger.info("✅ Bot execution completed!")

if __name__ == '__main__':
    asyncio.run(main())
