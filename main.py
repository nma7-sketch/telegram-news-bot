import asyncio
import logging
import os
from datetime import datetime, timezone

from fpdf import FPDF
from telegram import Bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TAMIL_FONT_PATH = os.getenv(
    'TAMIL_FONT_PATH',
    '/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf',
)

# Curated educational examples, not an exhaustive catalogue of plants.
PLANT_REACTIONS = [
    {
        'plant': 'Neem', 'compound': 'Azadirachtin',
        'reaction': 'Hydrolysis / oxidation (conceptual model)',
        'conditions': 'Illustrative aqueous, oxygen-exposed model; not a lab protocol',
        'equation': 'Azadirachtin + H2O -> hydrolysis products (simplified, not balanced)',
        'summary_en': 'Neem contains limonoids and phenolic compounds. This simplified model illustrates possible hydrolytic and oxidative transformations; actual products depend on the specific molecule and conditions.',
        'summary_ta': 'வேப்பிலையில் லிமோனாய்டுகள் மற்றும் பீனாலிக் சேர்மங்கள் உள்ளன. இந்த எளிய மாதிரி ஹைட்ரோலிசிஸ் மற்றும் ஆக்சிஜனேற்ற மாற்றங்களை விளக்குகிறது; உண்மையான தயாரிப்புகள் மூலக்கூறு மற்றும் சூழ்நிலைகளைப் பொறுத்தது.',
        'diagram': 'Plant compounds -- conceptual transformation --> possible product families',
    },
    {
        'plant': 'Tulsi', 'compound': 'Eugenol and related phenolics',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Illustrative oxygen-exposed model; not a lab protocol',
        'equation': 'Phenolic compound + O2 -> possible oxidation products (simplified)',
        'summary_en': 'Tulsi contains eugenol and other phenolics. Oxidation is a broad reaction class; this scheme is illustrative and does not specify experimentally verified products.',
        'summary_ta': 'துளசியில் ஈஜெனோல் உள்ளிட்ட பீனாலிக் சேர்மங்கள் உள்ளன. ஆக்சிஜனேற்றம் என்பது பரந்த வினை வகை; இங்கு காட்டப்படும் திட்டம் விளக்கத்திற்கானது, பரிசோதனையால் உறுதிப்படுத்தப்பட்ட தயாரிப்புகளைச் சுட்டிக்காட்டாது.',
        'diagram': 'Phenolic compound + O2 -- conceptual oxidation --> product family',
    },
    {
        'plant': 'Aloe Vera', 'compound': 'Aloin / anthraquinone glycosides',
        'reaction': 'Glycoside hydrolysis (conceptual model)',
        'conditions': 'Illustrative aqueous model; not a lab protocol',
        'equation': 'Glycoside + H2O -> aglycone + sugar (generalized)',
        'summary_en': 'Aloin is an anthraquinone glycoside. The generalized scheme shows how glycoside hydrolysis is represented in chemistry; it is not a procedure or a claim about a particular preparation.',
        'summary_ta': 'அலோயின் ஒரு ஆந்த்ராகுவினோன் கிளைகோசைடு. கிளைகோசைடு ஹைட்ரோலிசிஸை வேதியியலில் எவ்வாறு பொதுவாகக் காட்டுகிறோம் என்பதை இந்தத் திட்டம் விளக்குகிறது; இது தயாரிப்பு முறை அல்ல.',
        'diagram': 'Glycoside + H2O -- conceptual hydrolysis --> aglycone + sugar',
    },
    {
        'plant': 'Turmeric', 'compound': 'Curcumin',
        'reaction': 'Oxidative degradation (conceptual model)',
        'conditions': 'Illustrative light/oxygen model; not a lab protocol',
        'equation': 'Curcumin + oxidant -> possible degradation products (simplified)',
        'summary_en': 'Curcumin is a conjugated natural product. Light and oxygen can affect its stability; this diagram is a high-level conceptual illustration, not a fully specified reaction.',
        'summary_ta': 'கர்குமின் இணைந்த பிணைப்புகள் கொண்ட இயற்கைச் சேர்மமாகும். ஒளியும் ஆக்சிஜனும் அதன் நிலைத்தன்மையைப் பாதிக்கலாம்; இந்த வரைபடம் முழுமையாக வரையறுக்கப்பட்ட வினை அல்ல, கருத்து விளக்கம் மட்டுமே.',
        'diagram': 'Curcumin -- light / oxygen (conceptual) --> possible product families',
    },
    {
        'plant': 'Ginger', 'compound': 'Gingerols',
        'reaction': 'Thermal transformation (conceptual model)',
        'conditions': 'Illustrative heat-related model; not a lab protocol',
        'equation': 'Gingerol -> related compounds (simplified; conditions-dependent)',
        'summary_en': 'Ginger contains gingerols and related compounds. Heat-related transformations are discussed in food chemistry, but this generic scheme is not a recipe and does not predict a specific yield or product mixture.',
        'summary_ta': 'இஞ்சியில் ஜிஞ்செரால்கள் மற்றும் தொடர்புடைய சேர்மங்கள் உள்ளன. உணவு வேதியியலில் வெப்பத்தால் ஏற்படும் மாற்றங்கள் விவாதிக்கப்படுகின்றன; இந்தப் பொதுவான திட்டம் செய்முறை அல்ல, குறிப்பிட்ட தயாரிப்பையோ அளவையோ கணிக்காது.',
        'diagram': 'Gingerol -- conceptual heat-related change --> related compounds',
    },
    {
        'plant': 'Mint', 'compound': 'Menthol',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Generalized oxidation model; not a lab protocol',
        'equation': 'Secondary alcohol + oxidant -> ketone (general reaction class)',
        'summary_en': 'Menthol is a secondary alcohol. The diagram shows the general alcohol-to-ketone oxidation pattern; it is a textbook reaction class, not an instruction to treat plant material.',
        'summary_ta': 'மெந்தோல் ஒரு இரண்டாம் நிலை ஆல்கஹால். ஆல்கஹால் கீட்டோனாக மாறும் பொதுவான ஆக்சிஜனேற்ற வடிவத்தை வரைபடம் காட்டுகிறது; இது பாடநூல் கருத்து மட்டுமே.',
        'diagram': 'Secondary alcohol -- conceptual oxidation --> ketone',
    },
    {
        'plant': 'Lavender', 'compound': 'Linalool',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Generalized oxygen-exposure model; not a lab protocol',
        'equation': 'Terpene alcohol + O2 -> possible oxidation products (simplified)',
        'summary_en': 'Linalool is a terpene alcohol found in lavender. Its possible transformations depend on conditions; the scheme is deliberately generalized and does not prescribe an experiment.',
        'summary_ta': 'லாவெண்டரில் லினலூல் என்ற டெர்பீன் ஆல்கஹால் காணப்படுகிறது. அதன் மாற்றங்கள் சூழ்நிலைகளைப் பொறுத்தவை; இந்தத் திட்டம் பொதுவானது, பரிசோதனை வழிமுறையை வழங்காது.',
        'diagram': 'Terpene alcohol + O2 -- conceptual oxidation --> product family',
    },
    {
        'plant': 'Rosemary', 'compound': 'Carnosic acid',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Illustrative light/oxygen model; not a lab protocol',
        'equation': 'Carnosic acid + oxidant -> possible oxidation products (simplified)',
        'summary_en': 'Rosemary contains phenolic diterpenes, including carnosic acid. This high-level model illustrates oxidation as a possible transformation without asserting a single product or experimental condition.',
        'summary_ta': 'ரோஸ்மேரியில் கர்னோசிக் அமிலம் உள்ளிட்ட பீனாலிக் டைட்டர்பீன்கள் உள்ளன. ஒரே தயாரிப்பையோ பரிசோதனைச் சூழ்நிலையையோ உறுதிப்படுத்தாமல், ஆக்சிஜனேற்றத்தை சாத்தியமான மாற்றமாக இந்த மாதிரி விளக்குகிறது.',
        'diagram': 'Carnosic acid -- conceptual oxidation --> possible product family',
    },
    {
        'plant': 'Eucalyptus', 'compound': 'Eucalyptol',
        'reaction': 'Oxidation (conceptual model)',
        'conditions': 'Generalized oxygen-exposure model; not a lab protocol',
        'equation': 'Eucalyptol + oxidant -> possible oxygenated products (simplified)',
        'summary_en': 'Eucalyptol is a cyclic ether found in eucalyptus. The model introduces oxidation as a broad concept; specific transformations require verified chemical data and controlled research.',
        'summary_ta': 'யூகலிப்டஸில் யூகலிப்டால் என்ற வளைய ஈதர் காணப்படுகிறது. ஆக்சிஜனேற்றத்தைப் பொதுக் கருத்தாக இந்த மாதிரி அறிமுகப்படுத்துகிறது; குறிப்பிட்ட மாற்றங்களுக்கு உறுதிப்படுத்தப்பட்ட வேதியியல் தரவும் கட்டுப்படுத்தப்பட்ட ஆய்வும் தேவை.',
        'diagram': 'Eucalyptol -- conceptual oxidation --> possible product family',
    },
]


def get_hourly_plant():
    # UTC hour selects one entry; this is a curated rotation, not all plant species.
    return PLANT_REACTIONS[datetime.now(timezone.utc).hour % len(PLANT_REACTIONS)]


class ChemistryReportPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(220, 235, 255)
        self.cell(0, 10, 'Plant Chemistry Reaction Bulletin', new_x='LMARGIN', new_y='NEXT', fill=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}', align='C')


def create_pdf_for_plant(plant):
    if not os.path.isfile(TAMIL_FONT_PATH):
        raise FileNotFoundError(
            f'Tamil Unicode font not found at {TAMIL_FONT_PATH}. '
            'Install fonts-noto-core or set TAMIL_FONT_PATH.'
        )

    pdf = ChemistryReportPDF()
    pdf.add_font('NotoTamil', style='', fname=TAMIL_FONT_PATH)
    # HarfBuzz shapes Tamil glyphs correctly when uharfbuzz is installed.
    pdf.set_text_shaping()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    pdf.set_font('helvetica', 'B', 20)
    pdf.cell(0, 12, f'{plant["plant"]} Chemistry Model', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 7, f"Compound: {plant['compound']}\nReaction class: {plant['reaction']}\nModel scope: {plant['conditions']}")
    pdf.ln(3)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'English Summary', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 6, plant['summary_en'])
    pdf.ln(2)

    pdf.set_font('NotoTamil', '', 13)
    pdf.cell(0, 8, 'தமிழ் விளக்கம்', new_x='LMARGIN', new_y='NEXT')
    pdf.multi_cell(0, 7, plant['summary_ta'])
    pdf.ln(2)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Conceptual Reaction Scheme', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 7, plant['equation'])
    pdf.ln(1)
    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 7, 'Diagram (conceptual)', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('helvetica', '', 10)
    pdf.multi_cell(0, 6, '[ Reactants / plant compound ]  --->  [ possible product family ]')
    pdf.multi_cell(0, 6, plant['diagram'])
    pdf.ln(3)

    pdf.set_font('helvetica', 'B', 13)
    pdf.cell(0, 8, 'Safety and Scope', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('helvetica', '', 10)
    pdf.multi_cell(0, 6, 'Educational conceptual model only. It is not a validated reaction protocol, extraction method, medical advice, or instruction to apply any substance to people. Reaction products and conditions must be checked against reliable scientific sources.')

    output_name = f"{plant['plant'].lower().replace(' ', '_')}_plant_chemistry_report.pdf"
    pdf.output(output_name)
    logger.info('Generated PDF: %s', output_name)
    return output_name


async def send_pdf_to_channel(pdf_path):
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.info('Telegram credentials are not set; PDF generated locally: %s', pdf_path)
        return False

    try:
        bot = Bot(token=BOT_TOKEN)
        with open(pdf_path, 'rb') as pdf_file:
            await bot.send_document(
                chat_id=CHANNEL_ID,
                document=pdf_file,
                caption='Plant chemistry educational model only. Not medical advice or a human-application guide.',
            )
        logger.info('PDF uploaded to Telegram successfully.')
        return True
    except Exception:
        logger.exception('Failed to upload PDF to Telegram')
        raise


async def main():
    plant = get_hourly_plant()
    pdf_path = create_pdf_for_plant(plant)
    logger.info('Selected plant for this UTC hour: %s', plant['plant'])
    await send_pdf_to_channel(pdf_path)


if __name__ == '__main__':
    asyncio.run(main())
