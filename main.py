import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import tempfile

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TARGET_URL = "https://hft.md/jane-street/"

class NewsBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.posted_links_file = 'posted_links.json'
        self.load_posted_links()
    
    def load_posted_links(self):
        try:
            with open(self.posted_links_file, 'r') as f:
                self.posted_links = json.load(f)
                logger.info(f"Loaded {len(self.posted_links)} posted resources")
        except FileNotFoundError:
            self.posted_links = []
            logger.info("No posted links file found, starting fresh")
    
    def save_posted_links(self):
        with open(self.posted_links_file, 'w') as f:
            json.dump(self.posted_links, f, indent=2)
        logger.info("Saved posted resources")

    def is_file_or_video(self, title, description, link):
        """Filter to ONLY allow actual files (PDFs) and Videos/Talks"""
        title_lower = title.lower()
        desc_lower = description.lower()
        link_lower = link.lower()
        
        # 1. Direct file links (PDFs, Zips, CSVs, Videos)
        file_extensions = ['.pdf', '.mp4', '.mkv', '.avi', '.zip', '.csv', '.xlsx']
        if any(link_lower.endswith(ext) for ext in file_extensions):
            return True
            
        # 2. Strong keywords indicating a video, talk, or document
        media_keywords = ['video', 'talk', 'pdf', 'guide', 'primer', 'book', 'interview']
        if any(keyword in title_lower or keyword in desc_lower for keyword in media_keywords):
            return True
            
        return False

    def scrape_hft_md(self):
        """Scrape ONLY files and videos from hft.md/jane-street/"""
        logger.info(f"Scraping {TARGET_URL}...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        try:
            response = requests.get(TARGET_URL, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch webpage: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        items = []
        seen_titles = set()

        for tag in soup.find_all(['h2', 'h3', 'h4']):
            title = tag.get_text(strip=True)
            if not title or len(title) < 5 or title in seen_titles:
                continue
            
            parent = tag.parent
            a_tag = parent.find('a')
            
            link = ""
            if a_tag and a_tag.get('href'):
                link = a_tag['href']
                if not link.startswith('http'):
                    link = "https://hft.md" + link
            
            desc = ""
            p_tags = parent.find_all('p')
            if p_tags:
                desc = p_tags[0].get_text(strip=True)
                if len(desc) > 250:
                    desc = desc[:250] + "..."
            
            # APPLY THE FILTER HERE
            if title and link and self.is_file_or_video(title, desc, link):
                items.append({"title": title, "desc": desc, "link": link})
                seen_titles.add(title)

        logger.info(f"Found {len(items)} file/video resources (filtered out generic links).")
        return items

    async def download_and_upload_pdf(self, pdf_url, title, description):
        """Download PDF and upload directly to Telegram"""
        logger.info(f"📥 Downloading PDF: {pdf_url}")
        
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(pdf_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Check file size (Telegram limit is 50MB for bots)
            file_size_mb = len(response.content) / (1024 * 1024)
            logger.info(f"PDF size: {file_size_mb:.2f} MB")
            
            if file_size_mb > 50:
                logger.warning(f"⚠️ PDF too large ({file_size_mb:.2f} MB), sending as link instead")
                return False
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            logger.info(f"📤 Uploading PDF to Telegram: {title}")
            
            # Clean description for caption
            clean_desc = description[:1000] if len(description) > 1000 else description
            caption = f"📂 <b>{title}</b>\n\n{clean_desc}"
            
            # Upload to Telegram
            with open(tmp_path, 'rb') as pdf_file:
                await self.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=pdf_file,
                    caption=caption,
                    parse_mode='HTML',
                    disable_notification=False
                )
            
            # Clean up temp file
            os.unlink(tmp_path)
            logger.info(f"✅ Successfully uploaded PDF: {title}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to download PDF: {e}")
            return False
        except TelegramError as e:
            logger.error(f"❌ Telegram upload error: {e.message}")
            return False
        except Exception as e:
            logger.error(f" Unexpected error uploading PDF: {e}")
            return False
        finally:
            # Ensure temp file is deleted if it exists
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass

    async def send_resource(self, title, description, link):
        """Send resource - upload PDFs directly, send videos/other as links"""
        
        # Check if it's a PDF link
        if link.lower().endswith('.pdf'):
            logger.info(f" Detected PDF, attempting direct upload: {title}")
            success = await self.download_and_upload_pdf(link, title, description)
            
            if not success:
                # Fallback: send as link if upload fails
                logger.info(f"️ Upload failed, sending as link instead")
                return await self.send_as_link(title, description, link)
            return success
        else:
            # For videos and other resources, send as link
            return await self.send_as_link(title, description, link)

    async def send_as_link(self, title, description, link):
        """Send resource as a clickable link"""
        try:
            message = f"📂 <b>{title}</b>\n\n"
            message += f"{description}\n\n"
            message += f"🔗 <a href='{link}'>Access Resource</a>"
            
            await self.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            logger.info(f"✅ Posted link: {title}")
            return True
        except TelegramError as e:
            logger.error(f"❌ Telegram Error posting {title}: {e.message}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error posting {title}: {e}")
            return False

async def main():
    logger.info("=" * 50)
    logger.info("🚀 STARTING HFT.MD PDF UPLOADER BOT")
    logger.info("=" * 50)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("❌ Missing BOT_TOKEN or CHANNEL_ID in environment variables!")
        return
    
    bot = NewsBot()
    resources = bot.scrape_hft_md()
    
    if not resources:
        logger.warning("⚠️ No file/video resources found or scraping failed.")
        return

    new_posts_count = 0
    for item in resources:
        if item['link'] not in bot.posted_links:
            success = await bot.send_resource(item['title'], item['desc'], item['link'])
            if success:
                bot.posted_links.append(item['link'])
                new_posts_count += 1
                await asyncio.sleep(3) # Slightly longer delay for uploads
    
    if new_posts_count > 0:
        bot.save_posted_links()
        logger.info(f"✅ Successfully posted {new_posts_count} new resources!")
    else:
        logger.info("ℹ️ No new resources to post (all already shared).")
    
    logger.info("=" * 50)
    logger.info("✅ Bot execution completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
