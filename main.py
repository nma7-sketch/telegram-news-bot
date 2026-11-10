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
    # USA
    "BlackRock (USA)": "https://www.blackrock.com/us/individual/insights",
    "Vanguard (USA)": "https://investor.vanguard.com/investor-resources-education/market-commentary",
    "Bridgewater (USA)": "https://www.bridgewater.com/research-and-insights",
    "AQR Capital (USA)": "https://www.aqr.com/Insights",
    # Middle East
    "PIF (Saudi Arabia)": "https://www.pif.gov.sa/en/media-center/press-releases/",
    "Mubadala (UAE)": "https://www.mubadala.com/en/media/media-centre",
    "ADIA (UAE)": "https://www.adia.ae/en/media/press-releases.aspx",
    # Asia
    "GIC (Singapore)": "https://www.gic.com.sg/insights",
    "Temasek (Singapore)": "https://www.temasek.com.sg/en/news-and-insights",
    "Nomura (Japan)": "https://www.nomura.com/insights/",
    # Europe
    "Amundi (France)": "https://www.amundi.com/insights",
    "Allianz GI (Germany)": "https://www.allianzgi.com/insights",
    "Legal & General (UK)": "https://www.lgim.com/insights"
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

class GlobalIntelligenceBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.posted_links_file = 'posted_links.json'
        self.load_posted_links()
    
    def load_posted_links(self):
        try:
            with open(self.posted_links_file, 'r') as f: self.posted_links = json.load(f)
        except FileNotFoundError: self.posted_links = []

    def save_posted_links(self):
        with open(self.posted_links_file, 'w') as f: json.dump(self.posted_links, f, indent=2)

    def scrape_all_sources(self):
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
            asyncio.sleep(3) # Polite delay
            
        logger.info(f"📊 Found {len(all_resources)} new global insights.")
        return all_resources

    def generate_pdf_report(self, resources):
        """Create a professional PDF summary of the scraped data"""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 10, "Global Fund Manager Intelligence Report", ln=True, align="C")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", ln=True, align="C")
        pdf.ln(10)
        
        if not resources:
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(0, 10, "No new public insights published in the last 4 hours.", ln=True, align="C")
        else:
            # Group by Source
            grouped = {}
            for r in resources:
                grouped.setdefault(r['source'], []).append(r)
                
            for source, items in grouped.items():
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_fill_color(200, 220, 255)
                pdf.cell(0, 10, f" {source}", ln=True, fill=True)
                pdf.ln(2)
                
                pdf.set_font("Helvetica", "", 11)
                for item in items:
                    # Clean up title
                    title = item['title'][:100]
                    pdf.multi_cell(0, 6, f"• {title}")
                    pdf.set_text_color(0, 0, 255)
                    pdf.cell(0, 6, f"  Link: {item['link'][:80]}...", ln=True)
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
        logger.error("❌ Missing credentials!"); return
    
    bot = GlobalIntelligenceBot()
    resources = bot.scrape_all_sources()
    
    if resources:
        pdf_path = bot.generate_pdf_report(resources)
        await bot.send_pdf_to_channel(pdf_path, len(resources))
        
        # Mark as posted
        for r in resources: bot.posted_links.append(r['link'])
        bot.save_posted_links()
        os.remove(pdf_path) # Clean up
    else:
        logger.info("ℹ️ No new insights found. Skipping PDF generation.")

if __name__ == '__main__':
    asyncio.run(main())
