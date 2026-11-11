import os
import json
import logging
import requests
import feedparser
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
import asyncio
from fpdf import FPDF
from datetime import datetime
from urllib.parse import urljoin, urlparse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
CHANNEL_ID = (os.getenv('CHANNEL_ID') or '').strip()

# Approximate latest reported AUM / fund assets in USD billions. Reporting dates vary.
AUM_THRESHOLD_USD_BN = 500
FUND_MANAGER_SOURCES = [
    ("BlackRock (USA)", 11500, "https://www.blackrock.com/us/individual/insights"),
    ("Vanguard (USA)", 10100, "https://investor.vanguard.com/investor-resources-education/education/market-summary"),
    ("Fidelity Investments (USA)", 5500, "https://www.fidelity.com/learning-center/insights"),
    ("State Street Global Advisors (USA)", 4700, "https://www.ssga.com/us/en/intermediary/insights"),
    ("JPMorgan Asset Management (USA)", 4000, "https://am.jpmorgan.com/us/en/asset-management/adv/insights/"),
    ("Goldman Sachs Asset Management (USA)", 3100, "https://www.gsam.com/content/gsam/us/en/market-insights.html"),
    ("Capital Group (USA)", 2800, "https://www.capitalgroup.com/individual/insights.html"),
    ("UBS Asset Management (Switzerland)", 2800, "https://www.ubs.com/global/en/assetmanagement/insights.html"),
    ("PIMCO (USA)", 2000, "https://www.pimco.com/us/en/insights"),
    ("Allianz Global Investors (Germany)", 600, "https://www.allianzgi.com/en/insights"),
    ("Amundi (France)", 2300, "https://www.amundi.com/insights"),
    ("BNY Investments (USA)", 2000, "https://www.bny.com/investments/us/en/individual/insights.html"),
    ("Invesco (USA)", 1800, "https://www.invesco.com/us/en/insights.html"),
    ("Franklin Templeton (USA)", 1600, "https://www.franklintempleton.com/insights"),
    ("Northern Trust Asset Management (USA)", 1600, "https://www.northerntrust.com/united-states/insights-research"),
    ("T. Rowe Price (USA)", 1600, "https://www.troweprice.com/en/investment-institute/insights"),
    ("Morgan Stanley Investment Management (USA)", 1500, "https://www.morganstanley.com/insights"),
    ("PGIM (USA)", 1500, "https://www.pgim.com/insights"),
    ("Geode Capital Management (USA)", 1500, "https://www.geodecapital.com/"),
    ("Legal & General Investment Management (UK)", 1400, "https://www.lgim.com/insights"),
    ("BNP Paribas Asset Management (France)", 1400, "https://www.bnpparibas-am.com/en/how-we-think/"),
    ("Blackstone (USA)", 1200, "https://www.blackstone.com/insights/"),
    ("Brookfield Asset Management (Canada)", 1100, "https://www.brookfield.com/views-news/insights"),
    ("Schroders (UK)", 900, "https://www.schroders.com/en/global/individual/insights/"),
    ("Natixis Investment Managers (France)", 1200, "https://www.im.natixis.com/en-intl/insights"),
    ("Wellington Management (USA)", 1200, "https://www.wellington.com/en/insights/markets-and-outlooks"),
    ("Fidelity International (UK)", 900, "https://www.fidelityinternational.com/editorial/"),
    ("Dimensional Fund Advisors (USA)", 875, "https://www.dimensional.com/us-en/insights"),
    ("Nuveen (USA)", 1300, "https://www.nuveen.com/en-us/insights"),
    ("BMO Global Asset Management (Canada)", 700, "https://www.bmogam.com/ca-en/advisors/insights/"),
    ("Manulife Investment Management (Canada)", 1000, "https://www.manulifeim.com/institutional/ca/en/insights"),
    ("DWS (Germany)", 1000, "https://www.dws.com/insights/"),
    ("PIF (Saudi Arabia)", 1150, "https://www.pif.gov.sa/en/media-center/"),
    ("ADIA (UAE)", 1100, "https://www.adia.ae/en/publications"),
    ("GIC (Singapore)", 900, "https://www.gic.com.sg/newsroom/"),
    ("Norges Bank Investment Management (Norway)", 2000, "https://www.nbim.no/en/news-and-insights/"),
    ("China Investment Corporation (China)", 1300, "https://www.china-inv.cn/en/"),
    ("Kuwait Investment Authority (Kuwait)", 1000, "https://www.kia.gov.kw/"),
    ("Qatar Investment Authority (Qatar)", 510, "https://www.qia.qa/en/NewsRoom/Pages/default.aspx"),
]


def build_target_sources(sources, minimum_aum_usd_bn):
    return {
        name: url
        for name, aum_usd_bn, url in sources
        if aum_usd_bn > minimum_aum_usd_bn
    }


TARGET_SOURCES = build_target_sources(FUND_MANAGER_SOURCES, AUM_THRESHOLD_USD_BN)

TARGET_RSS_FEEDS = {
    "Kuwait Investment Authority (Kuwait)": "https://www.kia.gov.kw/feed/",
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

def parse_rss_feed(feed_content, source_name):
    feed = feedparser.parse(feed_content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Unable to parse RSS feed for {source_name}")

    resources = []
    for entry in feed.entries:
        title = BeautifulSoup(entry.get('title', ''), 'html.parser').get_text(" ", strip=True)
        link = entry.get('link', '').strip()
        if title and sanitize_text(title).strip() and urlparse(link).scheme in ('http', 'https'):
            resources.append({"title": title, "link": link, "source": source_name})
    return resources

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

    def scrape_source(self, source_name, url):
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        resources = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text(strip=True)
            full_url = urljoin(response.url, href)

            if len(text) > 20 and any(k in text.lower() for k in ['report', 'insight', 'outlook', 'market', 'update', 'release', 'pdf']):
                resources.append({"title": text, "link": full_url, "source": source_name})
        return resources

    async def scrape_all_sources(self):
        all_resources = []
        for source_name, page_url in TARGET_SOURCES.items():
            feed_url = TARGET_RSS_FEEDS.get(source_name)
            try:
                if feed_url:
                    logger.info(f"📰 Reading official RSS feed for {source_name}...")
                    response = requests.get(feed_url, headers=HEADERS, timeout=15)
                    response.raise_for_status()
                    resources = parse_rss_feed(response.content, source_name)
                else:
                    logger.info(f"🕵️ Scraping {source_name}...")
                    resources = self.scrape_source(source_name, page_url)
            except Exception as e:
                if feed_url:
                    logger.warning(f"⚠️ RSS feed failed for {source_name}; falling back to its official page: {e}")
                    try:
                        resources = self.scrape_source(source_name, page_url)
                    except Exception as fallback_error:
                        logger.warning(f"⚠️ Blocked/Failed {source_name}: {fallback_error}")
                        resources = []
                else:
                    logger.warning(f"⚠️ Blocked/Failed {source_name}: {e}")
                    resources = []

            for resource in resources:
                if resource['link'] not in self.posted_links and not any(r['link'] == resource['link'] for r in all_resources):
                    all_resources.append(resource)
            
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
            raise

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
