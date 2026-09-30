"""
memory/draft_store.py
Penyimpanan draft X & Threads yang menunggu review.
Tiap draft punya ID unik, jadi tombol di pesan Telegram lama tetap
mengacu ke draft miliknya sendiri (bukan draft terbaru).
"""
import json
import os
import uuid
from datetime import datetime, timedelta

STORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pending_drafts.json')
DAYS_TO_KEEP = 7


def _load():
    if not os.path.exists(STORE_FILE):
        return {}
    try:
        with open(STORE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save(store):
    # Tulis ke file sementara lalu rename, supaya file tidak rusak kalau proses mati di tengah
    tmp_path = STORE_FILE + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, STORE_FILE)


def _prune(store):
    """Buang draft yang lebih tua dari DAYS_TO_KEEP."""
    cutoff = datetime.now() - timedelta(days=DAYS_TO_KEEP)
    kept = {}
    for draft_id, entry in store.items():
        try:
            if datetime.fromisoformat(entry['timestamp']) > cutoff:
                kept[draft_id] = entry
        except Exception:
            continue
    return kept


def add(draft_text, signal_title):
    """Simpan draft baru, return ID-nya (dipakai di callback_data tombol)."""
    store = _prune(_load())
    draft_id = datetime.now().strftime('%Y%m%d%H%M') + uuid.uuid4().hex[:6]
    store[draft_id] = {
        'draft': draft_text,
        'signal': signal_title,
        'timestamp': datetime.now().isoformat(),
        'posted': {},  # platform -> hasil sukses, supaya retry tidak double-post
    }
    _save(store)
    return draft_id


def get(draft_id):
    return _load().get(draft_id)


def mark_posted(draft_id, platform, result):
    store = _load()
    if draft_id in store:
        store[draft_id].setdefault('posted', {})[platform] = result
        _save(store)


def remove(draft_id):
    store = _load()
    if store.pop(draft_id, None) is not None:
        _save(store)
