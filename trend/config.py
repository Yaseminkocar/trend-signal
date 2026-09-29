from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PATH = DATA_DIR / "records.jsonl"
PROFILES_PATH = DATA_DIR / "profiles.jsonl"
OUTPUT_DIR = ROOT / "output"
ISSUE_LOG = ROOT / "data" / "issues.jsonl"

TR_TZ = ZoneInfo("Europe/Istanbul")

EKSI_TOPICS = [
    "yurtiçi kargo",
    "aras kargo",
    "mng kargo",
    "ptt kargo",
    "sürat kargo",
    "trendyol express",
    "hepsijet",
    "kolay gelsin",
    "kargo",
]
EKSI_EXCLUDE_SLUG = r"ucag|tsk|askeri|kargo-gemisi|kargo-uzay"
EKSI_DAYS = 14
EKSI_MAX_PAGES_PER_TOPIC = 30

X_QUERIES = [
    'kargom lang:tr -filter:retweets',
    'kargo (gelmedi OR gecikti OR kayboldu OR hasarlı OR "teslim edildi") lang:tr -filter:retweets',
]
TIKTOK_QUERIES = [
    "kargo gecikti",
    "kargom gelmedi",
    "kargo şikayet",
    "kolay gelsin kargo",
    "hepsijet",
    "ptt kargo",
    "yurtiçi kargo",
    "aras kargo",
    "trendyol express kargo",
]
INSTAGRAM_TAGS = ["kargo", "kargogecikmesi", "kargosikayet", "yurtiçikargo", "hepsijet", "pttkargo"]

SIGNAL_SOURCES = ("eksi", "x")

X_TWEETS_PER_DAY = 25
X_PROFILE_HISTORY = 20

THEMES: dict[str, list[str]] = {
    "gecikme": ["gecik", "gelmedi", "hala gelmedi", "bekliyorum", "kaç gün", "günlerdir", "haftadır",
                "transfer merkez", "aktarma", "yolda görün", "dağıtıma çıkm", "varış şube", "gün oldu",
                "hafta oldu", "teslim etmedi", "teslim edemey", "geç geldi", "geç gel", "hareket görm"],
    "teslim_sorunu": ["teslim edildi görün", "teslim edilmiş görün", "teslim edildi yazıyor",
                      "teslim edilmedi", "adreste bulunamad", "alıcı bulunamad", "evde bulamad",
                      "evde bulunamad", "kapıyı çalm", "zili çalm", "zil çalm", "kapıya gelm", "kapıya kadar",
                      "şubeden teslim", "şubeye bırak", "şubeye git", "dağıtım ofis", "teslim alamıyor",
                      "dağıtım yapm", "notu bırak", "kapıya bırak"],
    "hasar_kayip": ["kırık", "kırıl", "hasar", "kayboldu", "kayıp", "ezil", "parçalan", "eksik ürün",
                    "eksik geld", "paket açılmış", "açılmış", "yırtık", "çalın"],
    "musteri_hizmetleri": ["müşteri hizmet", "çağrı merkez", "ulaşamıyorum", "ulaşılamıyor", "telefonu açm",
                           "şube açm", "whatsapp", "canlı destek", "şikayet ettim", "şikayetvar", "cimer",
                           "muhatap", "kimse ilgilenm"],
    "ucret_zam": ["zam ", "zamlan", "zamm", "ücret", "fiyat", "pahalı", "kargo bedava", "ücretsiz kargo",
                  "kargo bedel"],
    "kurye_davranisi": ["kurye", "dağıtıcı", "kaba ", "saygısız", "küfür", "bağır", "tavır", "terbiyesiz"],
    "olumlu_deneyim": ["hızlı geld", "erken geld", "ertesi gün geld", "sorunsuz", "memnun", "teşekkür",
                       "başarılı", "tavsiye ederim"],
    "genel_memnuniyetsizlik": ["rezil", "rezalet", "berbat", "en kötü", "sakın", "kullanmayın", "felaket",
                               "beceriksiz", "iğrenç", "bakkal dükkan"],
}

CARRIERS: dict[str, list[str]] = {
    "yurtici": ["yurtiçi", "yurtici"],
    "aras": ["aras kargo", "araskargo", "aras "],
    "mng": ["mng"],
    "ptt": ["ptt"],
    "surat": ["sürat kargo", "surat kargo", "sürat "],
    "trendyol_express": ["trendyol express", "trendyolexpress", "tex "],
    "hepsijet": ["hepsijet", "hepsi jet"],
    "kolay_gelsin": ["kolay gelsin kargo", "kolaygelsin", "kolay gelsin firma", "kolay gelsin şube", "kolay gelsin kurye"],
    "cargox": ["cargox"],
}
CARRIER_SLUGS: dict[str, str] = {
    "yurtici": "yurtici", "aras-kargo": "aras", "mng-kargo": "mng", "ptt-kargo": "ptt",
    "surat-kargo": "surat", "trendyol-express": "trendyol_express", "hepsijet": "hepsijet",
    "kolay-gelsin": "kolay_gelsin", "cargox": "cargox",
}

MIN_UNIQUE_CURRENT = 5
MIN_AUTHORS_CURRENT = 3
MIN_ACTIVE_DAYS_CURRENT = 3
MAX_SINGLE_DAY_SHARE = 0.6
MIN_SOURCES = 2
RISE_THRESHOLD = 1.0
