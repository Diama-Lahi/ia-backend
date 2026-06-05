import os
import re
import json
import logging
import requests
from functools import lru_cache
from collections import defaultdict, deque
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from groq import Groq

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -------------------------------------------------------------------
# BASES DE DONNÉES ABJAD
# -------------------------------------------------------------------
ABJAD_ORIENTAL = {
    'ا':1,'أ':1,'إ':1,'آ':1,'ٱ':1,
    'ب':2,'ت':400,'ث':500,'ج':3,'ح':8,'خ':600,
    'د':4,'ذ':700,'ر':200,'ز':7,'س':60,'ش':300,
    'ص':90,'ض':800,'ط':9,'ظ':900,'ع':70,'غ':1000,
    'ف':80,'ق':100,'ك':20,'ل':30,'م':40,'ن':50,
    'ه':5,'ة':5,'و':6,'ؤ':6,'ي':10,'ئ':10,'ى':10,'ء':1
}

ABJAD_MAGHRIBI = {
    **ABJAD_ORIENTAL,
    'ص':60,'ض':90,'ش':1000,'ظ':800,'غ':900,'س':300
}

NAMES_99 = [
    {"arabic":"الله","trans":"Allah","value":66},
    {"arabic":"الرحمن","trans":"Ar-Rahman","value":329},
    {"arabic":"الرحيم","trans":"Ar-Rahim","value":289},
    {"arabic":"الملك","trans":"Al-Malik","value":121},
    {"arabic":"القدوس","trans":"Al-Quddus","value":201},
    {"arabic":"السلام","trans":"As-Salam","value":162},
    {"arabic":"المؤمن","trans":"Al-Mu'min","value":167},
    {"arabic":"المهيمن","trans":"Al-Muhaymin","value":176},
    {"arabic":"العزيز","trans":"Al-Aziz","value":125},
    {"arabic":"الجبار","trans":"Al-Jabbar","value":237},
    {"arabic":"المتكبر","trans":"Al-Mutakabbir","value":662},
    {"arabic":"الخالق","trans":"Al-Khaliq","value":731},
    {"arabic":"البارئ","trans":"Al-Bari'","value":213},
    {"arabic":"المصور","trans":"Al-Musawwir","value":366},
    {"arabic":"الغفار","trans":"Al-Ghaffar","value":1281},
    {"arabic":"القهار","trans":"Al-Qahhar","value":306},
    {"arabic":"الوهاب","trans":"Al-Wahhab","value":14},
    {"arabic":"الرزاق","trans":"Ar-Razzaq","value":308},
    {"arabic":"الفتاح","trans":"Al-Fattah","value":489},
    {"arabic":"العليم","trans":"Al-Alim","value":150},
    {"arabic":"القابض","trans":"Al-Qabid","value":903},
    {"arabic":"الباسط","trans":"Al-Basit","value":72},
    {"arabic":"الخافض","trans":"Al-Khafid","value":881},
    {"arabic":"الرافع","trans":"Ar-Rafi'","value":351},
    {"arabic":"المعز","trans":"Al-Mu'izz","value":117},
    {"arabic":"المذل","trans":"Al-Mudhill","value":770},
    {"arabic":"السميع","trans":"As-Sami'","value":180},
    {"arabic":"البصير","trans":"Al-Basir","value":302},
    {"arabic":"الحكم","trans":"Al-Hakam","value":68},
    {"arabic":"العدل","trans":"Al-Adl","value":104},
    {"arabic":"اللطيف","trans":"Al-Latif","value":129},
    {"arabic":"الخبير","trans":"Al-Khabir","value":812},
    {"arabic":"الحليم","trans":"Al-Halim","value":88},
    {"arabic":"العظيم","trans":"Al-Azim","value":957},
    {"arabic":"الغفور","trans":"Al-Ghafur","value":1286},
    {"arabic":"الشكور","trans":"Ash-Shakur","value":526},
    {"arabic":"العلي","trans":"Al-Aliyy","value":110},
    {"arabic":"الكبير","trans":"Al-Kabir","value":232},
    {"arabic":"الحفيظ","trans":"Al-Hafiz","value":998},
    {"arabic":"المقيت","trans":"Al-Muqit","value":550},
    {"arabic":"الحسيب","trans":"Al-Hasib","value":80},
    {"arabic":"الجليل","trans":"Al-Jalil","value":73},
    {"arabic":"الكريم","trans":"Al-Karim","value":270},
    {"arabic":"الرقيب","trans":"Ar-Raqib","value":302},
    {"arabic":"المجيب","trans":"Al-Mujib","value":55},
    {"arabic":"الواسع","trans":"Al-Wasi'","value":137},
    {"arabic":"الحكيم","trans":"Al-Hakim","value":78},
    {"arabic":"الودود","trans":"Al-Wadud","value":20},
    {"arabic":"المجيد","trans":"Al-Majid","value":57},
    {"arabic":"الباعث","trans":"Al-Ba'ith","value":573},
    {"arabic":"الشهيد","trans":"Ash-Shahid","value":319},
    {"arabic":"الحق","trans":"Al-Haqq","value":108},
    {"arabic":"الوكيل","trans":"Al-Wakil","value":66},
    {"arabic":"القوي","trans":"Al-Qawiyy","value":116},
    {"arabic":"المتين","trans":"Al-Matin","value":500},
    {"arabic":"الولي","trans":"Al-Waliyy","value":46},
    {"arabic":"الحميد","trans":"Al-Hamid","value":62},
    {"arabic":"المحصي","trans":"Al-Muhsi","value":148},
    {"arabic":"المبدئ","trans":"Al-Mubdi'","value":86},
    {"arabic":"المعيد","trans":"Al-Mu'id","value":124},
    {"arabic":"المحيي","trans":"Al-Muhyi","value":68},
    {"arabic":"المميت","trans":"Al-Mumit","value":490},
    {"arabic":"الحي","trans":"Al-Hayy","value":18},
    {"arabic":"القيوم","trans":"Al-Qayyum","value":156},
    {"arabic":"الواجد","trans":"Al-Wajid","value":14},
    {"arabic":"الماجد","trans":"Al-Majid","value":48},
    {"arabic":"الواحد","trans":"Al-Wahid","value":19},
    {"arabic":"الصمد","trans":"As-Samad","value":134},
    {"arabic":"القادر","trans":"Al-Qadir","value":305},
    {"arabic":"المقتدر","trans":"Al-Muqtadir","value":744},
    {"arabic":"المقدم","trans":"Al-Muqaddim","value":184},
    {"arabic":"المؤخر","trans":"Al-Mu'akhkhir","value":846},
    {"arabic":"الأول","trans":"Al-Awwal","value":37},
    {"arabic":"الآخر","trans":"Al-Akhir","value":801},
    {"arabic":"الظاهر","trans":"Az-Zahir","value":1105},
    {"arabic":"الباطن","trans":"Al-Batin","value":62},
    {"arabic":"الوالي","trans":"Al-Wali","value":47},
    {"arabic":"المتعالي","trans":"Al-Muta'ali","value":551},
    {"arabic":"البر","trans":"Al-Barr","value":202},
    {"arabic":"التواب","trans":"At-Tawwab","value":409},
    {"arabic":"المنتقم","trans":"Al-Muntaqim","value":590},
    {"arabic":"العفو","trans":"Al-Afuww","value":156},
    {"arabic":"الرؤوف","trans":"Ar-Ra'uf","value":286},
    {"arabic":"مالك الملك","trans":"Malik al-Mulk","value":211},
    {"arabic":"ذو الجلال والإكرام","trans":"Dhu al-Jalal","value":1101},
    {"arabic":"المقسط","trans":"Al-Muqsit","value":209},
    {"arabic":"الجامع","trans":"Al-Jami'","value":114},
    {"arabic":"الغني","trans":"Al-Ghaniyy","value":1060},
    {"arabic":"المغني","trans":"Al-Mughni","value":1100},
    {"arabic":"المانع","trans":"Al-Mani'","value":121},
    {"arabic":"الضار","trans":"Ad-Darr","value":801},
    {"arabic":"النافع","trans":"An-Nafi'","value":201},
    {"arabic":"النور","trans":"An-Nur","value":256},
    {"arabic":"الهادي","trans":"Al-Hadi","value":15},
    {"arabic":"البديع","trans":"Al-Badi'","value":86},
    {"arabic":"الباقي","trans":"Al-Baqi","value":113},
    {"arabic":"الوارث","trans":"Al-Warith","value":707},
    {"arabic":"الرشيد","trans":"Ar-Rashid","value":514},
    {"arabic":"الصبور","trans":"As-Sabur","value":298}
]

FAMOUS_WORDS = [
    {"arabic":"بسم الله الرحمن الرحيم","trans":"Bismillah","value":786},
    {"arabic":"الله","trans":"Allah","value":66},
    {"arabic":"الرحمن","trans":"Ar-Rahman","value":329},
    {"arabic":"محمد","trans":"Muhammad ﷺ","value":92},
    {"arabic":"أحمد","trans":"Ahmad","value":53},
    {"arabic":"إبراهيم","trans":"Ibrahim","value":259},
    {"arabic":"موسى","trans":"Musa","value":116},
    {"arabic":"عيسى","trans":"Isa","value":150},
    {"arabic":"جبريل","trans":"Jibril","value":245},
    {"arabic":"القرآن","trans":"Al-Quran","value":382},
    {"arabic":"الإسلام","trans":"Al-Islam","value":163},
    {"arabic":"الإيمان","trans":"Al-Iman","value":133},
    {"arabic":"الجنة","trans":"Al-Jannah","value":89},
    {"arabic":"النار","trans":"An-Nar","value":282},
    {"arabic":"الحمد لله","trans":"Alhamdulillah","value":148},
    {"arabic":"سبحان الله","trans":"SubhanAllah","value":187},
    {"arabic":"الله أكبر","trans":"Allahu Akbar","value":289},
    {"arabic":"لا إله إلا الله","trans":"La ilaha illa Allah","value":165},
    {"arabic":"مكة","trans":"Makkah","value":65},
    {"arabic":"المدينة","trans":"Al-Madinah","value":140},
    {"arabic":"القدس","trans":"Al-Quds","value":195}
]

SURAH_NAMES = {
    1:"Al-Fatiha",2:"Al-Baqarah",3:"Ali 'Imran",4:"An-Nisa",5:"Al-Ma'idah",
    6:"Al-An'am",7:"Al-A'raf",8:"Al-Anfal",9:"At-Tawbah",10:"Yunus",
    11:"Hud",12:"Yusuf",13:"Ar-Ra'd",14:"Ibrahim",15:"Al-Hijr",
    16:"An-Nahl",17:"Al-Isra",18:"Al-Kahf",19:"Maryam",20:"Ta-Ha",
    21:"Al-Anbiya",22:"Al-Hajj",23:"Al-Mu'minun",24:"An-Nur",25:"Al-Furqan",
    26:"Ash-Shu'ara",27:"An-Naml",28:"Al-Qasas",29:"Al-'Ankabut",30:"Ar-Rum",
    31:"Luqman",32:"As-Sajdah",33:"Al-Ahzab",34:"Saba",35:"Fatir",
    36:"Ya-Sin",37:"As-Saffat",38:"Sad",39:"Az-Zumar",40:"Ghafir",
    41:"Fussilat",42:"Ash-Shura",43:"Az-Zukhruf",44:"Ad-Dukhan",45:"Al-Jathiyah",
    46:"Al-Ahqaf",47:"Muhammad",48:"Al-Fath",49:"Al-Hujurat",50:"Qaf",
    51:"Adh-Dhariyat",52:"At-Tur",53:"An-Najm",54:"Al-Qamar",55:"Ar-Rahman",
    56:"Al-Waqi'ah",57:"Al-Hadid",58:"Al-Mujadilah",59:"Al-Hashr",60:"Al-Mumtahanah",
    61:"As-Saff",62:"Al-Jumu'ah",63:"Al-Munafiqun",64:"At-Taghabun",65:"At-Talaq",
    66:"At-Tahrim",67:"Al-Mulk",68:"Al-Qalam",69:"Al-Haqqah",70:"Al-Ma'arij",
    71:"Nuh",72:"Al-Jinn",73:"Al-Muzzammil",74:"Al-Muddaththir",75:"Al-Qiyamah",
    76:"Al-Insan",77:"Al-Mursalat",78:"An-Naba",79:"An-Nazi'at",80:"'Abasa",
    81:"At-Takwir",82:"Al-Infitar",83:"Al-Mutaffifin",84:"Al-Inshiqaq",85:"Al-Buruj",
    86:"At-Tariq",87:"Al-A'la",88:"Al-Ghashiyah",89:"Al-Fajr",90:"Al-Balad",
    91:"Ash-Shams",92:"Al-Layl",93:"Ad-Duha",94:"Ash-Sharh",95:"At-Tin",
    96:"Al-'Alaq",97:"Al-Qadr",98:"Al-Bayyinah",99:"Az-Zalzalah",100:"Al-'Adiyat",
    101:"Al-Qari'ah",102:"At-Takathur",103:"Al-'Asr",104:"Al-Humazah",105:"Al-Fil",
    106:"Quraysh",107:"Al-Ma'un",108:"Al-Kawthar",109:"Al-Kafirun",110:"An-Nasr",
    111:"Al-Masad",112:"Al-Ikhlas",113:"Al-Falaq",114:"An-Nas"
}

# -------------------------------------------------------------------
# CHARGEMENT DE L'INDEX COMPLET DES VERSETS (si disponible)
# -------------------------------------------------------------------
VERSES_INDEX = {"oriental": {}, "maghribi": {}}
INDEX_FILE = os.path.join(os.path.dirname(__file__), "verses_abjad_index.json")
if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        raw_index = json.load(f)
    # Convertir les clés en entiers
    VERSES_INDEX["oriental"] = {int(k): v for k, v in raw_index.get("oriental", {}).items()}
    VERSES_INDEX["maghribi"] = {int(k): v for k, v in raw_index.get("maghribi", {}).items()}
    logger.info(f"✅ Index Abjad chargé : {len(VERSES_INDEX['oriental'])} valeurs orientales, {len(VERSES_INDEX['maghribi'])} maghrébines")
else:
    logger.warning("⚠️ Fichier verses_abjad_index.json introuvable. Recherche par valeur limitée.")

# -------------------------------------------------------------------
# FONCTIONS UTILITAIRES
# -------------------------------------------------------------------
def compute_abjad(text, order="oriental"):
    """Calcule la valeur Abjad d'un texte arabe"""
    abjad_map = ABJAD_MAGHRIBI if order == "maghribi" else ABJAD_ORIENTAL
    total = 0
    letters_count = 0
    for char in text:
        if char in abjad_map:
            total += abjad_map[char]
            letters_count += 1
    return {"total": total, "letters": letters_count, "order": order}

def find_name_by_value(value):
    """Trouve les noms d'Allah correspondant à une valeur"""
    return [n for n in NAMES_99 if n["value"] == value]

def find_name_by_text(text):
    """Trouve un nom d'Allah par son nom arabe ou translittéré"""
    results = []
    for n in NAMES_99:
        if (text.lower() in n["trans"].lower() or
            text in n["arabic"] or
            n["trans"].lower() in text.lower()):
            results.append(n)
    return results

def find_famous_word(query):
    """Recherche un mot célèbre par nom ou valeur"""
    results = []
    query_lower = query.lower().strip()
    if query_lower.isdigit():
        val = int(query_lower)
        results = [w for w in FAMOUS_WORDS if w["value"] == val]
    else:
        for w in FAMOUS_WORDS:
            if (query_lower in w["arabic"] or 
                query_lower in w["trans"].lower() or
                w["arabic"] in query_lower or
                w["trans"].lower() in query_lower):
                results.append(w)
    return results

def get_surah_info(number):
    if number in SURAH_NAMES:
        return {"number": number, "name": SURAH_NAMES[number]}
    return None

@lru_cache(maxsize=100)
def search_quran_verses(query):
    """Recherche des versets par mot-clé via l'API Al-Quran Cloud (cache activé)"""
    url = f"https://api.alquran.cloud/v1/search/{query}/all/en.asad"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 200:
                results = []
                for match in data["data"]["matches"][:5]:
                    results.append({
                        "surah_num": match["surah"]["number"],
                        "surah_name": match["surah"]["englishName"],
                        "ayah": match["ayahInSurah"],
                        "text": match["text"]
                    })
                return results
    except Exception as e:
        logger.error(f"Erreur recherche Coran: {e}")
    return []

# -------------------------------------------------------------------
# MÉMOIRE DE CONVERSATION (simple, en mémoire)
# -------------------------------------------------------------------
sessions = defaultdict(lambda: deque(maxlen=20))

def get_history(session_id):
    return list(sessions.get(session_id, []))

def add_to_history(session_id, role, content):
    sessions[session_id].append({"role": role, "content": content})

# -------------------------------------------------------------------
# PERSONNALITÉ DE L'ASSISTANT
# -------------------------------------------------------------------
ADAD_FINDER_PERSONALITY = """Tu es l'assistant IA officiel d'AdadFinder.com, un site islamique spécialisé dans le calcul Abjad (poids mystique des lettres arabes).

🎯 TON RÔLE :
Tu aides les utilisateurs à comprendre et utiliser AdadFinder. Tu es expert en :
- Calcul Abjad (oriental et maghrébin)
- Les 114 sourates du Saint Coran
- Les 99 noms d'Allah et leurs valeurs
- Les mots islamiques célèbres (Bismillah, Allah, Muhammad ﷺ, etc.)
- Statistiques et analyses de textes arabes

📚 CONNAISSANCES CLÉS :
- Bismillah (بسم الله الرحمن الرحيم) = 786 en Abjad
- Allah (الله) = 66
- Muhammad (محمد) = 92
- Ar-Rahman (الرحمن) = 329
- Al-Quran (القرآن) = 382
- Al-Islam (الإسلام) = 163
- Al-Jannah (الجنة) = 89
- Makkah (مكة) = 65
- Al-Madinah (المدينة) = 140

🗣️ STYLE :
- Réponds en français par défaut, mais tu peux utiliser l'arabe et l'anglais
- Sois respectueux, courtois et professionnel
- Utilise des emojis islamiques appropriés : ☪ 🕌 📖 ⭐ 🌙
- Commence par "As-salamu alaykum" si l'utilisateur salue
- Sois concis mais précis
- Ne calcule jamais une valeur Abjad toi-même ; utilise les données contextuelles fournies
- Ne donne jamais de versets du Coran que tu ne trouves pas dans le contexte
- Si une information n'est pas dans le contexte, dis-le honnêtement

🔍 UTILISATION DU CONTEXTE :
- Le contexte peut contenir des résultats de calcul, des noms, des versets
- Cite précisément ces données dans ta réponse
- Si plusieurs systèmes Abjad sont donnés, précise lequel est utilisé

⚠️ RÈGLES :
- Ne donne JAMAIS de conseils religieux personnels (fatwa, etc.)
- Redirige vers des savants qualifiés pour les questions religieuses complexes
- Reste toujours factuel et basé sur les données d'AdadFinder
- Ne fais pas de commentaires politiques
- Sois toujours respectueux envers toutes les traditions islamiques

🌐 SITE WEB :
Rappelle aux utilisateurs qu'ils peuvent utiliser les outils sur https://adadfinder.com pour :
- Calculer la valeur Abjad d'un texte libre
- Explorer les 114 sourates
- Rechercher par valeur dans le Coran
- Découvrir les 99 noms d'Allah
- Analyser des statistiques
"""

# -------------------------------------------------------------------
# CONSTRUCTION DU CONTEXTE (enrichi avec l'index complet des versets)
# -------------------------------------------------------------------
def build_context(user_message):
    """Analyse le message utilisateur et enrichit le contexte avec des données structurées"""
    context = ""
    msg_lower = user_message.lower()

    # Détection du système Abjad souhaité
    system_order = "oriental"
    if "maghrébin" in msg_lower or "maghribi" in msg_lower:
        system_order = "maghribi"

    # 1. Détection de demande de calcul explicite
    calc_match = re.search(r'(?:calcule|valeur(?:s)?\s*(?:abjad|numérique)?\s*(?:de|du|des?)?|combien\s+vaut)\s+(.+)', user_message, re.IGNORECASE)
    if calc_match:
        target = calc_match.group(1).strip()
        arabic_pattern = re.compile(r'[\u0621-\u064A]+')
        arabic_in_target = arabic_pattern.findall(target)
        if arabic_in_target:
            text_to_calc = ' '.join(arabic_in_target)
            or_result = compute_abjad(text_to_calc, "oriental")
            mg_result = compute_abjad(text_to_calc, "maghribi")
            context += f"\n\n📊 CALCUL ABJAD pour '{text_to_calc}':\n"
            context += f"- Oriental: {or_result['total']} ({or_result['letters']} lettres)\n"
            context += f"- Maghrébin: {mg_result['total']} ({mg_result['letters']} lettres)\n"
        else:
            words = find_famous_word(target)
            if words:
                for w in words:
                    abjad_val = compute_abjad(w["arabic"], system_order)["total"]
                    context += f"\n\n🌟 MOT CÉLÈBRE: {w['arabic']} ({w['trans']}) = {abjad_val} ({system_order})\n"

    # 2. Recherche par valeur numérique (si un nombre est présent)
    numbers = re.findall(r'\b(\d+)\b', user_message)
    for num in numbers:
        val = int(num)
        # Chercher dans les noms d'Allah
        names = find_name_by_value(val)
        if names:
            context += f"\n\n⭐ NOMS D'ALLAH avec valeur {val}:\n"
            for n in names:
                context += f"- {n['arabic']} ({n['trans']}) = {n['value']}\n"
        # Chercher dans les mots célèbres
        words = find_famous_word(num)
        if words:
            context += f"\n\n🌟 MOTS CÉLÈBRES avec valeur {val}:\n"
            for w in words:
                context += f"- {w['arabic']} ({w['trans']}) = {w['value']}\n"
        # Chercher une sourate par numéro
        surah = get_surah_info(val)
        if surah:
            context += f"\n\n📖 SOURATE {surah['number']}: {surah['name']}\n"
        
        # ★ Recherche dans l'index complet des versets
        verses_list = VERSES_INDEX.get(system_order, {}).get(val, [])
        if verses_list:
            context += f"\n\n📖 VERSET(S) AVEC LA VALEUR {val} (système {system_order}) :\n"
            for v in verses_list[:5]:  # limiter à 5 versets pour ne pas saturer le contexte
                surah_name = SURAH_NAMES.get(v['surah'], f"Sourate {v['surah']}")
                context += f"- {surah_name}, verset {v['ayah']} : {v['arabic']}\n"

    # 3. Recherche textuelle dans le Coran
    text_search_match = re.search(r'(?:recherche|trouve|cherche|verset.*contenant|mot)\s+(.+)', msg_lower)
    if text_search_match:
        query = text_search_match.group(1).strip()
        verses = search_quran_verses(query)
        if verses:
            context += f"\n\n📖 RÉSULTATS DE RECHERCHE POUR '{query}':\n"
            for v in verses:
                context += f"- S{v['surah_num']}:{v['ayah']} ({v['surah_name']}): {v['text']}\n"

    # 4. Recherche de nom d'Allah par texte
    name_matches = find_name_by_text(user_message)
    for name in name_matches:
        context += f"\n\n⭐ NOM D'ALLAH TROUVÉ: {name['arabic']} ({name['trans']}) = {name['value']}\n"

    # 5. Recherche de mots célèbres par texte
    word_matches = find_famous_word(user_message)
    for w in word_matches:
        abjad_val = compute_abjad(w["arabic"], system_order)["total"]
        context += f"\n\n🌟 MOT CÉLÈBRE: {w['arabic']} ({w['trans']}) = {abjad_val} ({system_order})\n"

    # 6. Détection de sourate par nom
    surah_name_match = re.search(r'(?:sourate|surah|سورة)\s*([a-zA-Zéèêëàâîïôûç\s-]+)', msg_lower, re.IGNORECASE)
    if surah_name_match:
        name_query = surah_name_match.group(1).strip().lower()
        for num, sname in SURAH_NAMES.items():
            if name_query in sname.lower():
                context += f"\n\n📖 SOURATE {num}: {sname}\n"
                break

    return context, system_order

# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "OK",
        "message": "AdadFinder AI Assistant est en ligne ☪",
        "endpoints": ["/chat", "/chat/stream"]
    }), 200

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not user_message:
        return jsonify({"error": "Message vide"}), 400

    logger.info(f"💬 [{session_id}] Question: {user_message[:50]}...")

    context, system_order = build_context(user_message)
    history = get_history(session_id)

    messages = [{"role": "system", "content": ADAD_FINDER_PERSONALITY}]
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"]})
    if context:
        messages.append({"role": "system", "content": f"📋 CONTEXTE ACTUEL :{context}"})
    messages.append({"role": "user", "content": user_message})

    try:
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=600
        )
        reply = r.choices[0].message.content
        logger.info(f"✅ [{session_id}] Réponse générée")

        add_to_history(session_id, "user", user_message)
        add_to_history(session_id, "assistant", reply)

        return jsonify({"reply": reply, "session_id": session_id})
    except Exception as e:
        logger.error(f"❌ Erreur: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not user_message:
        return jsonify({"error": "Message vide"}), 400

    context, system_order = build_context(user_message)
    history = get_history(session_id)

    messages = [{"role": "system", "content": ADAD_FINDER_PERSONALITY}]
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"]})
    if context:
        messages.append({"role": "system", "content": f"📋 CONTEXTE ACTUEL :{context}"})
    messages.append({"role": "user", "content": user_message})

    def generate():
        full_reply = ""
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=600,
                stream=True
            )
            for chunk in completion:
                token = chunk.choices[0].delta.content or ""
                if token:
                    full_reply += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
            add_to_history(session_id, "user", user_message)
            add_to_history(session_id, "assistant", full_reply)
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"❌ Erreur streaming: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(generate(), mimetype='text/event-stream')

# -------------------------------------------------------------------
# DÉMARRAGE
# -------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
