import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
import asyncio
from fpdf import FPDF
from datetime import datetime
from urllib.parse import urljoin

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# Global Fund Managers Database
TARGET_SOURCES = {
    "BlackRock (USA)": "https://www.blackrock.com/us/individual/insights",
    "Vanguard (USA)": "https://investor.vanguard.com/investor-resources-education/market-commentary",
    "Bridgewater (USA)": "https://www.bridgewater.com/research-and-insights",
    "AQR Capital (USA)": "https://www.aqr.com/Insights",
    "PIF (Saudi Arabia)": "https://www.pif.gov.sa/en/media-center/",
    "Mubadala (UAE)": "https://www.mubadala.com/en/media",
    "ADIA (UAE)": "https://www.adia.ae/en/media.aspx",
    "GIC (Singapore)": "https://www.gic.com.sg/",
    "Temasek (Singapore)": "https://www.temasek.com.sg/en/news-and-insights",
    "Nomura (Japan)": "https://www.nomura.com/",
    "Amundi (France)": "https://www.amundi.com/insights",
    "Allianz GI (Germany)": "https://www.allianzgi.com/insights",
    "Legal & General (UK)": "https://www.lgim.com/insights"
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def sanitize_text(text):
    """Replace problematic Unicode characters with standard ASCII for PDF generation"""
    replacements = {
        '\u2019': "'",  # Right single quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2026': '...', # Ellipsis
    }
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    # Fallback: strip any remaining non-ASCII characters
    return text.encode('ascii', 'ignore').decode('ascii')

class GlobalIntelligenceBot:
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

    async def scrape_all_sources(self):
        all_resources = []
        for source_name, url in TARGET_SOURCES.items():
            logger.info(f"🕵️ Scraping {source_name}...")
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    text = a_tag.get_text(strip=True)
                    full_url = urljoin(url, href)
                    
                    # Filter for actual reports/insights
                    if len(text) > 20 and any(k in text.lower() for k in ['report', 'insight', 'outlook', 'market', 'update', 'release', 'pdf']):
                        if full_url not in self.posted_links and not any(r['link'] == full_url for r in all_resources):
                            all_resources.append({"title": text, "link": full_url, "source": source_name})
            except Exception as e:
                logger.warning(f"⚠️ Blocked/Failed {source_name}: {e}")
            
            # Polite delay (properly awaited now)
            await asyncio.sleep(2) 
            
        logger.info(f"📊 Found {len(all_resources)} new global insights.")
        return all_resources

    def generate_pdf_report(self, resources):
        """Create a professional PDF summary of the scraped data"""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header (updated to fix deprecation warnings)
        pdf.set_font("helvetica", "B", 20)
        pdf.cell(0, 10, "Global Fund Manager Intelligence Report", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)
        
        if not resources:
            pdf.set_font("helvetica", "", 12)
            pdf.cell(0, 10, "No new public insights published in the last 4 hours.", new_x="LMARGIN", new_y="NEXT", align="C")
        else:
            # Group by Source
            grouped = {}
            for r in resources:
                grouped.setdefault(r['source'], []).append(r)
                
            for source, items in grouped.items():
                pdf.set_font("helvetica", "B", 14)
                pdf.set_fill_color(200, 220, 255)
                pdf.cell(0, 10, f" {source}", new_x="LMARGIN", new_y="NEXT", fill=True)
                pdf.ln(2)
                
                pdf.set_font("helvetica", "", 11)
                for item in items:
                    # Clean up title and SANITIZE for PDF
                    title = sanitize_text(item['title'][:100])
                    pdf.multi_cell(0, 6, f"- {title}")
                    pdf.set_text_color(0, 0, 255)
                    pdf.cell(0, 6, f"  Link: {sanitize_text(item['link'][:80])}...", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(3)
                pdf.ln(5)

        pdf_path = "Global_Intelligence_Report.pdf"
        pdf.output(pdf_path)
        logger.info(f"✅ PDF generated: {pdf_path}")
        return pdf_path

    async def send_pdf_to_channel(self, pdf_path, resource_count):
        try:
            caption = (
                f"🌍 <b>Global Fund Manager Intelligence Report</b>\n\n"
                f"📅 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"📊 <b>New Insights Found:</b> {resource_count}\n\n"
                f"Covering: BlackRock, Vanguard, PIF, Mubadala, GIC, Temasek, Amundi, and more.\n\n"
                f"📄 <i>Open the attached PDF for the full summary and direct links.</i>"
            )
            
            with open(pdf_path, 'rb') as pdf_file:
                await self.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=pdf_file,
                    caption=caption,
                    parse_mode='HTML'
                )
            logger.info("✅ PDF uploaded to Telegram successfully!")
        except Exception as e:
            logger.error(f"❌ Failed to upload PDF: {e}")

async def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("❌ Missing credentials!")
        return
    
    bot = GlobalIntelligenceBot()
    resources = await bot.scrape_all_sources()
    
    if resources:
        pdf_path = bot.generate_pdf_report(resources)
        await bot.send_pdf_to_channel(pdf_path, len(resources))
        
        # Mark as posted
        for r in resources: 
            bot.posted_links.append(r['link'])
        bot.save_posted_links()
        
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    else:
        logger.info("ℹ️ No new insights found. Skipping PDF generation.")

if __name__ == '__main__':
    asyncio.run(main())
