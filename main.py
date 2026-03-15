import imaplib
import email
import time
import threading
import requests
import os
from datetime import datetime
from email.header import decode_header

# ── Ayarlar (Railway Environment Variables'dan okunur) ──
GMAIL_USER     = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
BOT_TOKEN      = os.environ.get("BOT_TOKEN")

CHAT_IDS = {
    "XU030DJ2026": os.environ.get("CHAT_XU030"),
    "ETHUSDT":     os.environ.get("CHAT_ETHUSDT"),
    "DE40":        os.environ.get("CHAT_DE40"),
    "USTEC":       os.environ.get("CHAT_USTEC"),
}

REPEAT_COUNT    = 5
REPEAT_INTERVAL = 60
CHECK_INTERVAL  = 30
EMAIL_FILTER    = "Alert"

processed_ids = set()

def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        r.raise_for_status()
        print(f"  ✅ Mesaj gönderildi → {chat_id}")
    except Exception as e:
        print(f"  ❌ Hata: {e}")

def send_signals_repeated(instrument, signal_type):
    chat_id = CHAT_IDS.get(instrument)
    if not chat_id:
        print(f"  ⚠️ {instrument} için chat_id bulunamadı!")
        return

    emoji  = "🟢" if "BUY" in signal_type.upper() else "🔴"
    action = "📈 AL (BUY)" if emoji == "🟢" else "📉 SAT (SELL)"

    for i in range(1, REPEAT_COUNT + 1):
        zaman = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        mesaj = (
            f"{emoji} <b>SİNYAL — {i}/{REPEAT_COUNT}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Enstrüman :</b> {instrument}\n"
            f"📊 <b>İşlem      :</b> {action}\n"
            f"🕐 <b>Zaman      :</b> {zaman}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ TradingView Alarmı"
        )
        send_telegram(chat_id, mesaj)
        if i < REPEAT_COUNT:
            print(f"  ⏳ {REPEAT_INTERVAL}sn bekleniyor... ({i}/{REPEAT_COUNT})")
            time.sleep(REPEAT_INTERVAL)

    print(f"  ✅ {instrument} tamamlandı!")

def parse_email(subject, body):
    combined = (subject + " " + body).upper()

    instrument = None
    for inst in CHAT_IDS.keys():
        if inst.upper() in combined:
            instrument = inst
            break

    if "BUY" in combined or "AL" in combined or "LONG" in combined:
        signal = "BUY"
    elif "SELL" in combined or "SAT" in combined or "SHORT" in combined:
        signal = "SELL"
    else:
        signal = "BUY"

    return instrument, signal

def check_gmail():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, f'(UNSEEN SUBJECT "{EMAIL_FILTER}")')
        if status != "OK":
            mail.logout()
            return

        email_ids = messages[0].split()
        if not email_ids:
            mail.logout()
            return

        print(f"\n📬 {len(email_ids)} yeni email!")

        for eid in email_ids:
            if eid in processed_ids:
                continue

            _, msg_data = mail.fetch(eid, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    subject_raw = msg.get("Subject", "")
                    subject, enc = decode_header(subject_raw)[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(enc or "utf-8", errors="ignore")

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                    print(f"  📧 {subject}")
                    instrument, signal = parse_email(subject, body)

                    if instrument:
                        print(f"  🎯 {instrument} | {signal}")
                        t = threading.Thread(
                            target=send_signals_repeated,
                            args=(instrument, signal),
                            daemon=True
                        )
                        t.start()
                    else:
                        print("  ⚠️ Enstrüman tespit edilemedi!")

            processed_ids.add(eid)

        mail.logout()

    except Exception as e:
        print(f"❌ Gmail hatası: {e}")

def main():
    print("=" * 45)
    print("🚀 TV Sinyal Bot Başladı!")
    print(f"📧 Gmail: {GMAIL_USER}")
    print(f"🔄 Kontrol: her {CHECK_INTERVAL}sn")
    print(f"📨 Tekrar: {REPEAT_COUNT}x / {REPEAT_INTERVAL}sn ara")
    print("=" * 45)

    while True:
        print(f"\n🔍 [{datetime.now().strftime('%H:%M:%S')}] Gmail kontrol ediliyor...")
        check_gmail()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
