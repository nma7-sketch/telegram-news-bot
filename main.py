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

PLANT_REACTIONS = [
    {
        'plant': 'Neem',
        'compound': 'Azadirachtin',
        'reaction': 'Hydrolysis / Oxidation',
        'conditions': 'Aqueous buffer, pH 7.2, 30–40°C',
        'equation': 'Azadirachtin + H2O -> hydrolyzed terpenoid products + oxidized by-products',
        'summary_en': 'Neem is rich in limonoids and phenolic compounds. In a simplified educational model, the active molecules can undergo hydrolysis and oxidative transformation under warm, buffered aqueous conditions.',
        'summary_ta': 'வேப்ப மரம் லிமோனாய்டுகள் மற்றும் பீனாலிக் சேர்மங்களை கொண்டுள்ளது. எளிமையான கல்விப் மாதிரியில், சூடான நீர்-அடிப்படையிலான நிலைமைகளில் செயலில் உள்ள மூலக்கூறுகள் ஹைட்ரோலிசிஸ் மற்றும் ஆக்சிஃபைலேஷனில் ஈடுபடலாம்.',
        'diagram': 'Plant matrix -> [aqueous buffer, 30-40°C] -> hydrolyzed fragments -> oxidized products',
        'safety': 'This is a conceptual chemistry model for education only. It is not a treatment guide or a skin-use instruction.'
    },
    {
        'plant': 'Tulsi',
        'compound': 'Eugenol',
        'reaction': 'Oxidation / Esterification',
        'conditions': 'Air exposure, mild heat, neutral solvent',
        'equation': 'Eugenol + O2 -> oxidized phenolic products + resinous intermediates',
        'summary_en': 'Tulsi contains eugenol and related phenolics. In a classroom model, oxygen and mild heat can promote oxidation to more stable aromatic products.',
        'summary_ta': 'துளசி ஈஜெனோல் மற்றும் தொடர்புடைய பீனாலிக் சேர்மங்களைக் கொண்டுள்ளது. வகுப்பறை மாதிரியில், ஆக்ஸிஜன் மற்றும் லேசான வெப்பம் ஆகியவை அதிக ஸ்திரத்தன்மை கொண்ட அரோமாட்டிக் பொருட்களாக ஆக்சிஜனேற்றத்தை தூண்டலாம்.',
        'diagram': 'Eugenol + O2 -> phenolic oxidation products -> resinous compounds',
        'safety': 'This is an educational reaction model only and must not be interpreted as a human-application procedure.'
    },
    {
        'plant': 'Aloe Vera',
        'compound': 'Aloin / anthraquinone glycosides',
        'reaction': 'Hydrolysis',
        'conditions': 'Water, pH 5-7, mild warming',
        'equation': 'Aloin glycoside + H2O -> aglycone + sugar fragments',
        'summary_en': 'Aloe contains anthraquinone glycosides that can hydrolyze in aqueous conditions, producing smaller aromatic fragments under mild, non-extreme conditions.',
        'summary_ta': 'அலோவேராவில் ஆந்த்ராகுவினோன் கிளைகோசைடுகள் உள்ளன. நீரில் இது ஹைட்ரோலிசிஸ் அடைந்து, லேசான வெப்ப நிலைகளில் சிறிய அரோமாட்டிக் பகுப்புகளாக மாறலாம்.',
        'diagram': 'Glycoside -> [H2O, mild heat] -> aglycone + sugar fragments',
        'safety': 'This is a chemistry concept model, not a preparation or skin-use protocol.'
    },
    {
        'plant': 'Turmeric',
        'compound': 'Curcumin',
        'reaction': 'Photochemical oxidation',
        'conditions': 'Light exposure, oxygen, neutral solvent',
        'equation': 'Curcumin + O2 + light -> oxidized diketone products + degraded fragments',
        'summary_en': 'Curcumin is a diarylheptanoid whose conjugated system is highly sensitive to light and oxygen. In a simplified model, oxidative degradation can lead to smaller fragments.',
        'summary_ta': 'மஞ்சள் நிறத்தில் உள்ள கர்குமின் ஒரு டைஆரில்ஹெப்டனாய்டு. அதன் கன்ஜுகேடட் அமைப்பு ஒளி மற்றும் ஆக்ஸிஜனை எதிர்கொள்ளும்போது ஆக்சிடேடிவ் சிதைவை சந்திக்கலாம்.',
        'diagram': 'Curcumin + light + O2 -> oxidized diketone fragments',
        'safety': 'The content is educational only and is not a recommendation for direct human use.'
    },
    {
        'plant': 'Ginger',
        'compound': 'Gingerol',
        'reaction': 'Thermal degradation / oxidation',
        'conditions': 'Heat above 60°C and oxygen exposure',
        'equation': 'Gingerol + O2 + heat -> shogaol + oxidized aldehyde products',
        'summary_en': 'Gingerols are pungent phenolic compounds. Heating in the presence of oxygen can convert them to shogaols and related oxidized products in a simplified reaction model.',
        'summary_ta': 'இஞ்சியில் ஜிங்கரோல்கள் உள்ளன. ஆக்ஸிஜன் மற்றும் வெப்பத்துடன் சேரும்போது, அவை ஷோகால்ஸ் மற்றும் தொடர்புடைய ஆக்சிஜனேற்றப் பொருட்களாக மாற்றமடையலாம்.',
        'diagram': 'Gingerol -> [heat + O2] -> shogaol + aldehyde fragments',
        'safety': 'This is an educational simulation of chemistry, not a skin treatment method.'
    },
    {
        'plant': 'Mint',
        'compound': 'Menthol',
        'reaction': 'Oxidation / dehydration',
        'conditions': 'Air exposure, elevated temperature',
        'equation': 'Menthol + O2 -> menthone + oxidized terpenoid species',
        'summary_en': 'Menthol can be oxidized under warm, oxygen-rich conditions to compounds such as menthone and related terpenoid oxidation products in a theoretical framework.',
        'summary_ta': 'மெந்தோல், வெப்பம் மற்றும் ஆக்ஸிஜன் இருப்பில் மெந்தோன் மற்றும் பிற டெர்பெனாய்டு ஆக்சிஜனேற்றப் பொருட்களாக மாற்றமடையலாம்.',
        'diagram': 'Menthol + O2 -> menthone + oxidized terpenoid products',
        'safety': 'Conceptual chemistry education only; not a direct-use recommendation.'
    },
    {
        'plant': 'Lavender',
        'compound': 'Linalool',
        'reaction': 'Oxidation / rearrangement',
        'conditions': 'Air exposure and moderate heat',
        'equation': 'Linalool + O2 -> linalyl oxide + oxidized monoterpene products',
        'summary_en': 'Lavender contains linalool, a monoterpene alcohol that can convert to oxide and oxidized products under oxygen-rich and warm conditions in educational models.',
        'summary_ta': 'லாவெண்டர் லினலோல் என்ற மானோடெர்பீன் ஆல்கஹாலை கொண்டுள்ளது. ஆக்ஸிஜன் மற்றும் லேசான வெப்பம் இருப்பில் இது லினாலில் ஆக்சைடு போன்ற தயாரிப்புகளாக மாறலாம்.',
        'diagram': 'Linalool -> [O2 + warmth] -> linalyl oxide + oxidation products',
        'safety': 'This is informational and not a treatment or application protocol.'
    },
    {
        'plant': 'Rosemary',
        'compound': 'Carnosic acid',
        'reaction': 'Oxidation / decarboxylation',
        'conditions': 'Oxygen, light, neutral solvent',
        'equation': 'Carnosic acid + O2 + light -> oxidized abietane products + decarboxylated fragments',
        'summary_en': 'Rosemary is rich in phenolic diterpenes. Under oxygen and light, carnosic acid can undergo oxidation and fragmentation in a simplified reaction model.',
        'summary_ta': 'ரோஸ்மேரி ஃபீனாலிக் டைட்டர்பீன்களை கொண்டுள்ளது. ஆக்ஸிஜன் மற்றும் ஒளி இருப்பில் கர்னோசிக் அமிலம் ஆக்சிஜனேற்றம் மற்றும் பகுப்புக்கு உட்படலாம்.',
        'diagram': 'Carnosic acid + O2 + light -> oxidized abietane products',
        'safety': 'Educational chemistry only; no direct-use claims are implied.'
    },
    {
        'plant': 'Eucalyptus',
        'compound': 'Eucalyptol',
        'reaction': 'Oxidation',
        'conditions': 'Oxygen, heat, acidic or neutral medium',
        'equation': 'Eucalyptol + O2 -> oxygenated terpenoid products + minor fragments',
        'summary_en': 'Eucalyptus contains eucalyptol, a cyclic ether with a terpene skeleton. Under heat and oxidation in an educational model, oxygenated products can form through auto-oxidation.',
        'summary_ta': 'யூகலிப்டஸ் ஆலையில் யூகலிப்டோல் உள்ளது. வெப்பம் மற்றும் ஆக்ஸிஜன் இருப்பில் இது ஓவ்ஸிஜனேற்றத்தினால் ஆக்ஸிஜன் சேர்மங்களாக மாற்றமடையலாம்.',
        'diagram': 'Eucalyptol + O2 -> oxygenated terpenoid products',
        'safety': 'This content is conceptual and is not an application instruction.'
    },
]


def get_hourly_plant():
    utc_now = datetime.now(timezone.utc)
    index = utc_now.hour % len(PLANT_REACTIONS)
    return PLANT_REACTIONS[index]


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
    pdf = ChemistryReportPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font('helvetica', 'B', 20)
    pdf.cell(0, 12, f'{plant["plant"]} Chemistry Model', ln=True, align='C')
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 7, f"Compound: {plant['compound']}\nReaction class: {plant['reaction']}\nConditions: {plant['conditions']}")
    pdf.ln(3)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'English Summary', ln=True)
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 6, plant['summary_en'])
    pdf.ln(2)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'தமிழ் விளக்கம்', ln=True)
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 6, plant['summary_ta'])
    pdf.ln(2)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Conceptual Reaction Scheme', ln=True)
    pdf.set_font('helvetica', 'B', 12)
    pdf.multi_cell(0, 8, plant['equation'])
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 6, 'Diagram (conceptual):')
    pdf.multi_cell(0, 6, plant['diagram'])
    pdf.ln(2)

    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 8, 'Safety and Scope', ln=True)
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 6, plant['safety'])
    pdf.ln(4)

    output_name = f"{plant['plant'].lower().replace(' ', '_')}_plant_chemistry_report.pdf"
    pdf.output(output_name)
    logger.info('✅ Generated PDF: %s', output_name)
    return output_name


async def send_pdf_to_channel(pdf_path):
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.info('ℹ️ Telegram credentials not set. Skipping send. Local PDF ready: %s', pdf_path)
        return False

    try:
        bot = Bot(token=BOT_TOKEN)
        with open(pdf_path, 'rb') as pdf_file:
            await bot.send_document(
                chat_id=CHANNEL_ID,
                document=pdf_file,
                caption=(
                    '🌿 Plant Chemistry Reaction Bulletin\n\n'
                    'This is an educational chemistry model only.\n'
                    'No direct treatment or application guidance is implied.'
                ),
                parse_mode='HTML',
            )
        logger.info('✅ PDF uploaded to Telegram successfully.')
        return True
    except Exception as exc:  # pragma: no cover - runtime Telegram failure
        logger.error('❌ Failed to upload PDF: %s', exc)
        return False


async def main():
    plant = get_hourly_plant()
    pdf_path = create_pdf_for_plant(plant)
    await send_pdf_to_channel(pdf_path)


if __name__ == '__main__':
    asyncio.run(main())
