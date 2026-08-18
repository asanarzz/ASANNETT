"""
forward_email.py

Checks an email inbox (via IMAP) for unread messages, saves the body of
each one as a .txt file, and sends that file to Eitaa via the eitaayar.ir
bot API. Designed to run repeatedly (e.g. every 5 minutes) via GitHub
Actions, so it only processes messages it hasn't seen before.

Required environment variables (set as GitHub Actions "Secrets"):
  EMAIL_HOST      e.g. imap.gmail.com
  EMAIL_USER      your full email address
  EMAIL_PASS      an app password (NOT your normal password, see notes)
  EITAA_TOKEN     token from eitaayar.ir
  EITAA_CHAT_ID   your numeric Eitaa chat id from eitaayar.ir
"""

import imaplib
import email
from email.header import decode_header
import os
import re
import requests

EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EITAA_TOKEN = os.environ["EITAA_TOKEN"]
EITAA_CHAT_ID = os.environ["EITAA_CHAT_ID"]

EITAA_SEND_FILE_URL = f"https://eitaayar.ir/api/{EITAA_TOKEN}/sendFile"


def decode_mime_words(s):
    if not s:
        return ""
    parts = decode_header(s)
    decoded = ""
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded += text.decode(charset or "utf-8", errors="ignore")
        else:
            decoded += text
    return decoded


def get_plain_text_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                charset = part.get_content_charset() or "utf-8"
                try:
                    return part.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
        # fallback: no plain text part found, try html stripped of tags
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                html = part.get_payload(decode=True).decode(charset, errors="ignore")
                return re.sub("<[^<]+?>", "", html)
        return "(بدون متن قابل نمایش)"
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            return msg.get_payload(decode=True).decode(charset, errors="ignore")
        except Exception:
            return msg.get_payload(decode=True).decode("utf-8", errors="ignore")


def safe_filename(subject):
    subject = subject or "email"
    subject = re.sub(r'[\\/*?:"<>|]', "", subject)
    subject = subject.strip()[:60] or "email"
    return subject + ".txt"


def send_txt_to_eitaa(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    with open(filename, "rb") as f:
        files = {"file": (filename, f, "text/plain")}
        data = {"chat_id": EITAA_CHAT_ID, "caption": filename}
        resp = requests.post(EITAA_SEND_FILE_URL, data=data, files=files, timeout=30)

    os.remove(filename)

    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text}
    print(f"Eitaa response for {filename}: {result}")
    return result


def main():
    imap = imaplib.IMAP4_SSL(EMAIL_HOST)
    imap.login(EMAIL_USER, EMAIL_PASS)
    imap.select("INBOX")

    status, data = imap.search(None, "UNSEEN")
    if status != "OK":
        print("Could not search inbox.")
        return

    message_ids = data[0].split()
    if not message_ids:
        print("No new emails.")
        imap.logout()
        return

    print(f"Found {len(message_ids)} new email(s).")

    for msg_id in message_ids:
        # Fetching with RFC822 (not BODY.PEEK) marks the message as read,
        # which is what prevents us from resending it next run.
        status, msg_data = imap.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_mime_words(msg.get("Subject"))
        sender = decode_mime_words(msg.get("From"))
        body = get_plain_text_body(msg)

        full_content = f"از: {sender}\nموضوع: {subject}\n\n{body}"
        filename = safe_filename(subject)

        send_txt_to_eitaa(filename, full_content)

    imap.logout()


if __name__ == "__main__":
    main()
