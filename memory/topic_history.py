"""
memory/topic_history.py
Tracker topik yang sudah dipakai — mencegah tema yang sama muncul berulang.
"""
import json
import os
from datetime import datetime, timedelta

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'used_topics.json')
DAYS_TO_REMEMBER = 7

# Stopwords yang diabaikan saat cek kemiripan
_STOPWORDS = {
    'yang', 'dan', 'di', 'ke', 'dari', 'ini', 'itu', 'dengan', 'untuk', 'atau',
    'the', 'a', 'an', 'is', 'of', 'to', 'in', 'and', 'for', 'on', 'how', 'my',
    'i', 'me', 'we', 'you', 'he', 'she', 'it', 'are', 'was', 'be', 'by'
}


def load():
    """Load riwayat topik 7 hari terakhir."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cutoff = datetime.now() - timedelta(days=DAYS_TO_REMEMBER)
        return [e for e in data if datetime.fromisoformat(e['date']) > cutoff]
    except Exception:
        return []


def save(title, cluster=""):
    """Simpan topik yang baru dipakai ke riwayat."""
    history = load_all()
    history.append({
        'title': title,
        'cluster': cluster,
        'date': datetime.now().isoformat()
    })
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_all():
    """Load semua riwayat tanpa filter tanggal (untuk write-back)."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _tokenize(text):
    words = set(text.lower().replace('[reddit]', '').replace('[sistem]', '').split())
    return words - _STOPWORDS


def is_duplicate(title, threshold=0.45):
    """
    Return True jika title terlalu mirip dengan salah satu topik 7 hari terakhir.
    threshold=0.45 → 45% kata yang sama sudah dianggap duplikat.
    """
    history = load()
    if not history:
        return False

    title_words = _tokenize(title)
    if not title_words:
        return False

    for entry in history:
        past_words = _tokenize(entry['title'])
        if not past_words:
            continue
        overlap = len(title_words & past_words) / len(title_words)
        if overlap >= threshold:
            return True
    return False


def get_used_clusters():
    """Return daftar cluster yang sudah dipakai 7 hari terakhir."""
    return [e.get('cluster', '') for e in load()]
