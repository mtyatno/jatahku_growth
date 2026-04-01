# scraper/trend_scraper.py
import requests
import xml.etree.ElementTree as ET
import sys
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Tambah memory ke path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from memory import topic_history

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
FRESHNESS_HOURS = 72  # Ambil post maks 72 jam terakhir

# ==========================================
# FALLBACK BANK — 20 ide bergilir
# Dipilih berdasarkan (hari ke-N % len(bank))
# ==========================================
FALLBACK_BANK = [
    "Gaji 5 juta tapi tiap hari ngopi 50rb",
    "Uang habis sebelum tanggal 20, padahal baru gajian",
    "Nggak tahu uang habis ke mana tiap bulan",
    "Cicilan kartu kredit yang nggak ada habisnya",
    "Beli sesuatu karena diskon padahal nggak butuh",
    "Transfer sana-sini tapi saldo tetap tipis",
    "Makan siang di luar tiap hari bikin tekor",
    "Utang ke teman karena malu pinjam bank",
    "Gaji naik tapi pengeluaran tetap lebih besar",
    "Nabung niat, tapi selalu kepake sebelum akhir bulan",
    "Beli skincare mahal tapi nggak ada dana darurat",
    "Bayar tagihan bulanan yang makin banyak",
    "Ghosting tagihan karena takut lihat nominalnya",
    "Bingung harus pilih nabung atau bayar utang dulu",
    "Impulsif belanja online tiap malam",
    "THR habis dalam seminggu tanpa sadar",
    "Nggak punya dana darurat, panik pas ada keperluan mendadak",
    "Jajan receh tiap hari yang totalnya mengejutkan",
    "Nonton konten orang kaya bikin makin boros",
    "Lifestyle inflation: gaji naik, gaya hidup ikut naik",
]


def _is_fresh(published_str):
    """Return True jika post dalam FRESHNESS_HOURS terakhir. Jika gagal parse, anggap fresh."""
    if not published_str:
        return True
    try:
        pub_dt = parsedate_to_datetime(published_str)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_HOURS)
        return pub_dt >= cutoff
    except Exception:
        return True


def get_reddit_ideas():
    """Scrape beberapa subreddit keuangan Indonesia via RSS."""
    subreddits = [
        "r/finansial",
        "r/keuangan",
        "r/indonesia",   # broader, untuk sinyal umum
        "r/povertyfinance",
        "r/personalfinance",
    ]
    ideas = []

    for sub in subreddits:
        url = f"https://www.reddit.com/{sub}/new.rss"
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ {sub} RSS ditolak ({response.status_code})")
                continue

            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)

            count = 0
            for entry in entries:
                if count >= 5:
                    break
                title_el = entry.find('atom:title', ns)
                published_el = entry.find('atom:published', ns)
                if title_el is None:
                    continue

                published_str = published_el.text if published_el is not None else None
                if not _is_fresh(published_str):
                    continue  # Lewati post lama

                title = title_el.text
                # Filter relevan (keuangan / pain point)
                keywords = ['gaji', 'uang', 'utang', 'tabungan', 'hemat', 'boros',
                            'cicilan', 'kredit', 'broke', 'salary', 'debt', 'budget',
                            'spending', 'money', 'financial', 'invest', 'nabung']
                if any(kw in title.lower() for kw in keywords):
                    ideas.append(f"[{sub}] {title}")
                    count += 1

            if count > 0:
                print(f"✅ {sub}: {count} ide segar ditemukan")
            else:
                print(f"ℹ️ {sub}: tidak ada ide relevan hari ini")

        except Exception as e:
            print(f"❌ Error {sub}: {e}")

    return ideas


def get_apify_ideas():
    """Placeholder Apify — aktifkan jika sudah punya Actor."""
    if not hasattr(config, 'APIFY_API_TOKEN') or config.APIFY_API_TOKEN == "PASTE_TOKEN_APIFY_DI_SINI":
        return []
    return []


def get_fallback_idea():
    """Pilih 1 ide dari fallback bank berdasarkan hari ke-N (selalu berbeda tiap hari)."""
    day_index = datetime.now().timetuple().tm_yday  # 1–365
    idea = FALLBACK_BANK[day_index % len(FALLBACK_BANK)]
    print(f"⚠️ Menggunakan ide fallback rotasi hari ke-{day_index}: {idea}")
    return f"[FALLBACK] {idea}"


def get_daily_ideas():
    print("Mencari ide konten untuk Jatahku Growth Engine...")
    reddit_ideas = get_reddit_ideas()
    apify_ideas = get_apify_ideas()

    all_ideas = reddit_ideas + apify_ideas

    # Filter duplikat dari riwayat 7 hari
    fresh_ideas = [idea for idea in all_ideas if not topic_history.is_duplicate(idea)]
    skipped = len(all_ideas) - len(fresh_ideas)
    if skipped > 0:
        print(f"🔁 {skipped} ide dilewati (duplikat dari 7 hari terakhir)")

    if not fresh_ideas:
        print("⚠️ Semua scraper kosong/duplikat, pakai fallback rotasi.")
        fresh_ideas = [get_fallback_idea()]

    formatted = []
    for i, idea in enumerate(fresh_ideas[:5], 1):
        formatted.append(f"{i}. {idea}")

    return formatted


if __name__ == "__main__":
    hasil = get_daily_ideas()
    print("\n--- HASIL TANGKAPAN HARI INI ---")
    for h in hasil:
        print(h)
