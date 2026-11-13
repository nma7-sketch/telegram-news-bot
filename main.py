import asyncio
import logging
import os
from datetime import datetime, timezone

from fpdf import FPDF
from telegram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# GitHub secrets can accidentally include a trailing newline; strip whitespace
# before the token becomes part of Telegram's API URL.
BOT_TOKEN = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
CHANNEL_ID = (os.getenv('CHANNEL_ID') or '').strip()
TAMIL_FONT_PATH = os.getenv('TAMIL_FONT_PATH', '/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf').strip()

# Curated educational examples, not an exhaustive catalogue of plants.
PLANT_REACTIONS = [
    {
        'plant': 'Neem', 'compound': 'Azadirachtin',
        'reaction': 'Hydrolysis / oxidation (conceptual model)',
        'conditions': 'Illustrative aqueous, oxygen-exposed model; not a lab protocol',
        'equation': 'Azadirachtin + H2O -> hydrolysis products (simplified, not balanced)',
        'en': 'Neem contains limonoids and phenolic compounds. This simplified model illustrates possible hydrolytic and oxidative transformations; actual products depend on the specific molecule and conditions.',
        'ta': 'வேப்பிலையில் லிமோனாய்டுகள் மற்றும் பீனாலிக் சேர்மங்கள் உள்ளன. இந்த எளிய மாதிரி ஹைட்ரோலிசிஸ் மற்றும் ஆக்சிஜனேற்ற மாற்றங்களை விளக்குகிறது; உண்மையான தயாரிப்புகள் மூலக்கூறு மற்றும் சூழ்நிலைகளைப் பொறுத்தது.',
        'diagram': 'Plant compounds -> conceptual transformation -> possible product families',
    },
    {
        'plant': 'Tulsi', 'compound': 'Eugenol and related phenolics',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Illustrative oxygen-exposed model; not a lab protocol',
        'equation': 'Phenolic compound + O2 -> possible oxidation products (simplified)',
        'en': 'Tulsi contains eugenol and other phenolics. Oxidation is a broad reaction class; this scheme is illustrative and does not specify experimentally verified products.',
        'ta': 'துளசியில் ஈஜெனோல் உள்ளிட்ட பீனாலிக் சேர்மங்கள் உள்ளன. ஆக்சிஜனேற்றம் என்பது பரந்த வினை வகை; இங்கு காட்டப்படும் திட்டம் விளக்கத்திற்கானது, பரிசோதனையால் உறுதிப்படுத்தப்பட்ட தயாரிப்புகளைச் சுட்டிக்காட்டாது.',
        'diagram': 'Phenolic compound + O2 -> conceptual oxidation -> product family',
    },
    {
        'plant': 'Aloe Vera', 'compound': 'Aloin / anthraquinone glycosides',
        'reaction': 'Glycoside hydrolysis (conceptual model)',
        'conditions': 'Illustrative aqueous model; not a lab protocol',
        'equation': 'Glycoside + H2O -> aglycone + sugar (generalized)',
        'en': 'Aloin is an anthraquinone glycoside. The generalized scheme shows how glycoside hydrolysis is represented in chemistry; it is not a procedure or a claim about a particular preparation.',
        'ta': 'அலோயின் ஒரு ஆந்த்ராகுவினோன் கிளைகோசைடு. கிளைகோசைடு ஹைட்ரோலிசிஸை வேதியியலில் எவ்வாறு பொதுவாகக் காட்டுகிறோம் என்பதை இந்தத் திட்டம் விளக்குகிறது; இது தயாரிப்பு முறை அல்ல.',
        'diagram': 'Glycoside + H2O -> conceptual hydrolysis -> aglycone + sugar',
    },
    {
        'plant': 'Turmeric', 'compound': 'Curcumin',
        'reaction': 'Oxidative degradation (conceptual model)',
        'conditions': 'Illustrative light/oxygen model; not a lab protocol',
        'equation': 'Curcumin + oxidant -> possible degradation products (simplified)',
        'en': 'Curcumin is a conjugated natural product. Light and oxygen can affect its stability; this diagram is a high-level conceptual illustration, not a fully specified reaction.',
        'ta': 'கர்குமின் இணைந்த பிணைப்புகள் கொண்ட இயற்கைச் சேர்மமாகும். ஒளியும் ஆக்சிஜனும் அதன் நிலைத்தன்மையைப் பாதிக்கலாம்; இந்த வரைபடம் முழுமையாக வரையறுக்கப்பட்ட வினை அல்ல, கருத்து விளக்கம் மட்டுமே.',
        'diagram': 'Curcumin + light / oxygen -> conceptual change -> possible products',
    },
    {
        'plant': 'Ginger', 'compound': 'Gingerols',
        'reaction': 'Thermal transformation (conceptual model)',
        'conditions': 'Illustrative heat-related model; not a lab protocol',
        'equation': 'Gingerol -> related compounds (simplified; conditions-dependent)',
        'en': 'Ginger contains gingerols and related compounds. Heat-related transformations are discussed in food chemistry, but this generic scheme is not a recipe and does not predict a specific yield or product mixture.',
        'ta': 'இஞ்சியில் ஜிஞ்செரால்கள் மற்றும் தொடர்புடைய சேர்மங்கள் உள்ளன. உணவு வேதியியலில் வெப்பத்தால் ஏற்படும் மாற்றங்கள் விவாதிக்கப்படுகின்றன; இந்தப் பொதுவான திட்டம் செய்முறை அல்ல, குறிப்பிட்ட தயாரிப்பையோ அளவையோ கணிக்காது.',
        'diagram': 'Gingerol -> conceptual heat-related change -> related compounds',
    },
    {
        'plant': 'Mint', 'compound': 'Menthol',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Generalized oxidation model; not a lab protocol',
        'equation': 'Secondary alcohol + oxidant -> ketone (general reaction class)',
        'en': 'Menthol is a secondary alcohol. The diagram shows the general alcohol-to-ketone oxidation pattern; it is a textbook reaction class, not an instruction to treat plant material.',
        'ta': 'மெந்தோல் ஒரு இரண்டாம் நிலை ஆல்கஹால். ஆல்கஹால் கீட்டோனாக மாறும் பொதுவான ஆக்சிஜனேற்ற வடிவத்தை வரைபடம் காட்டுகிறது; இது பாடநூல் கருத்து மட்டுமே.',
        'diagram': 'Secondary alcohol -> conceptual oxidation -> ketone',
    },
    {
        'plant': 'Lavender', 'compound': 'Linalool',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Generalized oxygen-exposure model; not a lab protocol',
        'equation': 'Terpene alcohol + O2 -> possible oxidation products (simplified)',
        'en': 'Linalool is a terpene alcohol found in lavender. Its possible transformations depend on conditions; the scheme is deliberately generalized and does not prescribe an experiment.',
        'ta': 'லாவெண்டரில் லினலூல் என்ற டெர்பீன் ஆல்கஹால் காணப்படுகிறது. அதன் மாற்றங்கள் சூழ்நிலைகளைப் பொறுத்தவை; இந்தத் திட்டம் பொதுவானது, பரிசோதனை வழிமுறையை வழங்காது.',
        'diagram': 'Terpene alcohol + O2 -> conceptual oxidation -> product family',
    },
    {
        'plant': 'Rosemary', 'compound': 'Carnosic acid',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Illustrative light/oxygen model; not a lab protocol',
        'equation': 'Carnosic acid + oxidant -> possible oxidation products (simplified)',
        'en': 'Rosemary contains phenolic diterpenes, including carnosic acid. This high-level model illustrates oxidation as a possible transformation without asserting a single product or experimental condition.',
        'ta': 'ரோஸ்மேரியில் கர்னோசிக் அமிலம் உள்ளிட்ட பீனாலிக் டைட்டர்பீன்கள் உள்ளன. ஒரே தயாரிப்பையோ பரிசோதனைச் சூழ்நிலையையோ உறுதிப்படுத்தாமல், ஆக்சிஜனேற்றத்தை சாத்தியமான மாற்றமாக இந்த மாதிரி விளக்குகிறது.',
        'diagram': 'Carnosic acid -> conceptual oxidation -> possible product family',
    },
    {
        'plant': 'Eucalyptus', 'compound': 'Eucalyptol',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Generalized oxygen-exposure model; not a lab protocol',
        'equation': 'Eucalyptol + oxidant -> possible oxygenated products (simplified)',
        'en': 'Eucalyptol is a cyclic ether found in eucalyptus. The model introduces oxidation as a broad concept; specific transformations require verified chemical data and controlled research.',
        'ta': 'யூகலிப்டஸில் யூகலிப்டால் என்ற வளைய ஈதர் காணப்படுகிறது. ஆக்சிஜனேற்றத்தைப் பொதுக் கருத்தாக இந்த மாதிரி அறிமுகப்படுத்துகிறது; குறிப்பிட்ட மாற்றங்களுக்கு உறுதிப்படுத்தப்பட்ட வேதியியல் தரவும் கட்டுப்படுத்தப்பட்ட ஆய்வும் தேவை.',
        'diagram': 'Eucalyptol -> conceptual oxidation -> possible product family',
    },
]


def get_hourly_plant():
    return PLANT_REACTIONS[datetime.now(timezone.utc).hour % len(PLANT_REACTIONS)]


def write_wrapped(pdf, text, font='helvetica', style='', size=11, line_height=6):
    pdf.set_font(font, style, size)
    pdf.set_x(pdf.l_margin)
    width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(width, line_height, text)


class ChemistryReportPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(220, 235, 255)
        self.set_x(self.l_margin)
        width = self.w - self.l_margin - self.r_margin
        self.cell(width, 10, 'Plant Chemistry Reaction Bulletin', new_x='LMARGIN', new_y='NEXT', fill=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}', align='C')


def create_pdf_for_plant(plant):
    if not os.path.isfile(TAMIL_FONT_PATH):
        raise FileNotFoundError(f'Tamil Unicode font not found: {TAMIL_FONT_PATH}')
    pdf = ChemistryReportPDF()
    pdf.set_margins(12, 12, 12)
    pdf.add_font('NotoTamil', style='', fname=TAMIL_FONT_PATH)
    pdf.set_text_shaping()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font('helvetica', 'B', 20)
    pdf.set_x(pdf.l_margin)
    pdf.cell(width, 12, f'{plant["plant"]} Chemistry Model', new_x='LMARGIN', new_y='NEXT', align='C')
    write_wrapped(pdf, f"Compound: {plant['compound']}\nReaction class: {plant['reaction']}\nModel scope: {plant['conditions']}")
    pdf.ln(3)
    write_wrapped(pdf, 'English Summary', style='B', size=14, line_height=8)
    write_wrapped(pdf, plant['en'])
    pdf.ln(2)
    write_wrapped(pdf, 'தமிழ் விளக்கம்', font='NotoTamil', size=13, line_height=8)
    write_wrapped(pdf, plant['ta'], font='NotoTamil', size=12, line_height=7)
    pdf.ln(2)
    write_wrapped(pdf, 'Conceptual Reaction Scheme', style='B', size=14, line_height=8)
    write_wrapped(pdf, plant['equation'])
    pdf.ln(1)
    write_wrapped(pdf, 'Diagram (conceptual)', style='B', size=11, line_height=7)
    write_wrapped(pdf, '[ Reactants / plant compound ]  ->  [ possible product family ]', size=10)
    write_wrapped(pdf, plant['diagram'], size=10)
    pdf.ln(3)
    write_wrapped(pdf, 'Safety and Scope', style='B', size=13, line_height=8)
    write_wrapped(pdf, 'Educational conceptual model only. It is not a validated reaction protocol, extraction method, medical advice, or instruction to apply any substance to people. Reaction products and conditions must be checked against reliable scientific sources.', size=10)

    filename = f"{plant['plant'].lower().replace(' ', '_')}_plant_chemistry_report.pdf"
    pdf.output(filename)
    logger.info('Generated PDF: %s', filename)
    return filename


async def send_pdf_to_channel(pdf_path):
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.info('Telegram credentials are not set; PDF generated locally: %s', pdf_path)
        return False
    bot = Bot(token=BOT_TOKEN)
    with open(pdf_path, 'rb') as pdf_file:
        await bot.send_document(
            chat_id=CHANNEL_ID,
            document=pdf_file,
            caption='Plant chemistry educational model only. Not medical advice or a human-application guide.',
        )
    logger.info('PDF uploaded to Telegram successfully.')
    return True


async def main():
    plant = get_hourly_plant()
    logger.info('Selected plant for this UTC hour: %s', plant['plant'])
    pdf_path = create_pdf_for_plant(plant)
    await send_pdf_to_channel(pdf_path)


if __name__ == '__main__':
    asyncio.run(main())
