# bot_center/callback_bot.py
# Jalankan terus-menerus (python callback_bot.py) untuk menangani tombol inline Telegram.
import sys
import os
import json
import time
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bot_center.poster import post_all

PENDING_DRAFT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'memory', 'pending_draft.json'
)

API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def get_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["callback_query"]}
    if offset is not None:
        params["offset"] = offset
    try:
        r = requests.get(f"{API}/getUpdates", params=params, timeout=35)
        return r.json()
    except Exception as e:
        print(f"⚠️ getUpdates error: {e}")
        return {"result": []}


def answer_callback(callback_id, text="✅"):
    requests.post(f"{API}/answerCallbackQuery", json={
        "callback_query_id": callback_id,
        "text": text
    }, timeout=10)


def edit_message(chat_id, message_id, new_text):
    requests.post(f"{API}/editMessageText", json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "HTML"
    }, timeout=10)


def send_message(text):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=10)


def load_pending_draft():
    if not os.path.exists(PENDING_DRAFT_PATH):
        return None
    try:
        with open(PENDING_DRAFT_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def handle_post(cb_id, chat_id, message_id):
    pending = load_pending_draft()
    if not pending:
        answer_callback(cb_id, "⚠️ Tidak ada draft tersimpan.")
        return

    answer_callback(cb_id, "⏳ Sedang posting...")
    edit_message(chat_id, message_id, "⏳ <b>Posting ke X &amp; Threads...</b>")

    results = post_all(pending["draft"])
    result_lines = "\n".join(results.values())

    send_message(
        f"📬 <b>Hasil Posting:</b>\n{result_lines}"
    )
    edit_message(
        chat_id, message_id,
        f"📝 <b>DRAFT (sudah diposting):</b>\n<code>{pending['draft']}</code>"
    )

    # Hapus pending draft setelah berhasil diposting
    try:
        os.remove(PENDING_DRAFT_PATH)
    except Exception:
        pass


def handle_skip(cb_id, chat_id, message_id):
    answer_callback(cb_id, "⏭️ Draft dilewati.")
    edit_message(
        chat_id, message_id,
        "⏭️ <b>Draft dilewati — tidak diposting.</b>"
    )


def main():
    print("🤖 Callback Bot aktif — menunggu tombol review draft...")
    offset = None

    while True:
        updates = get_updates(offset)

        for update in updates.get("result", []):
            offset = update["update_id"] + 1

            if "callback_query" not in update:
                continue

            cb = update["callback_query"]
            cb_id = cb["id"]
            data = cb.get("data", "")
            chat_id = cb["message"]["chat"]["id"]
            message_id = cb["message"]["message_id"]

            print(f"📥 Callback diterima: {data}")

            if data == "post_draft":
                handle_post(cb_id, chat_id, message_id)
            elif data == "skip_draft":
                handle_skip(cb_id, chat_id, message_id)

        time.sleep(1)


if __name__ == "__main__":
    main()
