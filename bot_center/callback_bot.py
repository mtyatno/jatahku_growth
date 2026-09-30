# bot_center/callback_bot.py
# Jalankan terus-menerus (python callback_bot.py) untuk menangani tombol inline Telegram.
import sys
import os
import time
import html
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from bot_center.poster import post_all, PLATFORMS
from memory import draft_store

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


def _call(method, payload):
    """Panggil Telegram API dan log kalau Telegram menolak (ok=false)."""
    try:
        r = requests.post(f"{API}/{method}", json=payload, timeout=10)
        data = r.json()
        if not data.get("ok"):
            print(f"❌ Telegram {method} ditolak: {data.get('description')}")
        return data
    except Exception as e:
        print(f"❌ Telegram {method} error: {e}")
        return {}


def answer_callback(callback_id, text="✅"):
    _call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


def edit_message(chat_id, message_id, new_text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    _call("editMessageText", payload)


def send_message(text):
    _call("sendMessage", {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })


def retry_buttons(draft_id):
    return {"inline_keyboard": [[
        {"text": "🔁 Coba Lagi", "callback_data": f"post_draft:{draft_id}"},
        {"text": "❌ Batalkan", "callback_data": f"skip_draft:{draft_id}"}
    ]]}


def handle_post(cb_id, chat_id, message_id, draft_id):
    pending = draft_store.get(draft_id)
    if not pending:
        answer_callback(cb_id, "⚠️ Draft sudah diproses atau kadaluarsa.")
        return

    answer_callback(cb_id, "⏳ Sedang posting...")
    edit_message(chat_id, message_id, "⏳ <b>Posting ke X &amp; Threads...</b>")

    already_posted = pending.get("posted", {})
    results = post_all(pending["draft"], skip=already_posted.keys())

    for platform, (ok, msg) in results.items():
        if ok:
            draft_store.mark_posted(draft_id, platform, msg)
            already_posted[platform] = msg

    result_lines = "\n".join(html.escape(msg) for _, msg in results.values())
    send_message(f"📬 <b>Hasil Posting:</b>\n{result_lines}")

    draft_html = html.escape(pending["draft"])
    failed = [p for p in PLATFORMS if p not in already_posted]

    if not failed:
        edit_message(
            chat_id, message_id,
            f"📝 <b>DRAFT (sudah diposting):</b>\n<code>{draft_html}</code>"
        )
        draft_store.remove(draft_id)
    else:
        # Draft tetap disimpan; tombol retry hanya memposting ulang platform yang gagal
        edit_message(
            chat_id, message_id,
            f"📝 <b>DRAFT (gagal di: {', '.join(failed)}):</b>\n<code>{draft_html}</code>",
            reply_markup=retry_buttons(draft_id)
        )


def handle_skip(cb_id, chat_id, message_id, draft_id):
    draft_store.remove(draft_id)
    answer_callback(cb_id, "⏭️ Draft dilewati.")
    edit_message(
        chat_id, message_id,
        "⏭️ <b>Draft dilewati — tidak diposting.</b>"
    )


def handle_done(cb_id, chat_id, message_id, draft_id):
    pending = draft_store.get(draft_id)
    draft_store.remove(draft_id)
    answer_callback(cb_id, "✅ Ditandai sudah diposting.")
    text = "✅ <b>Draft ditandai sudah diposting.</b>"
    if pending:
        text += f"\n<code>{html.escape(pending['draft'])}</code>"
    edit_message(chat_id, message_id, text)


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

            action, _, draft_id = data.partition(":")
            if not draft_id:
                # Tombol format lama (tanpa ID draft) — tidak bisa dipastikan draft mana
                answer_callback(cb_id, "⚠️ Tombol versi lama, draft tidak bisa diproses.")
                continue

            if action == "post_draft":
                handle_post(cb_id, chat_id, message_id, draft_id)
            elif action == "skip_draft":
                handle_skip(cb_id, chat_id, message_id, draft_id)
            elif action == "done_draft":
                handle_done(cb_id, chat_id, message_id, draft_id)

        time.sleep(1)


if __name__ == "__main__":
    main()
