# ==========================================================
#  CRAWLER: tự động gửi lệnh /checkvc cho bot SFAST,
#  đọc câu trả lời của bot, tách các mã ra, lưu vào data.json
#  Dành cho người mới — đọc kỹ hướng dẫn bên dưới
# ==========================================================
#
# BƯỚC 1 — Lấy API_ID và API_HASH (làm 1 lần duy nhất):
#   Vào https://my.telegram.org -> "API development tools" -> lấy 2 giá trị
#
# BƯỚC 2 — Cài thư viện (chạy trong terminal/cmd):
#   pip install telethon
#
# BƯỚC 3 — Chạy lần đầu (chỉ để đăng nhập, tạo file phiên):
#   python crawler.py
#   -> nhập số điện thoại + mã Telegram gửi về khi được hỏi
#
# Khi chạy tự động trên GitHub Actions, dùng biến môi trường:
#   TG_API_ID, TG_API_HASH, TELEGRAM_SESSION (đọc bên dưới)
# ==========================================================

import json
import os
import re
import time
from datetime import datetime, timezone
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# ---------- CẤU HÌNH ----------
API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
BOT_USERNAME = "sfast_main_bot"   # tên bot cần hỏi mã
COMMAND = "/checkvc"              # lệnh để bot trả về danh sách mã
WAIT_SECONDS = 4                  # thời gian đợi mỗi lần kiểm tra (thử lại tối đa 6 lần)
# -------------------------------------------------

SESSION_NAME = "voucher_session"
OUTPUT_FILE = "data.json"


def get_bot_reply(client) -> str:
    """Gửi lệnh cho bot và lấy nội dung tin nhắn trả lời gần nhất của bot.
    Thử kiểm tra nhiều lần trong lúc đợi, vì server chạy tự động có thể
    phản hồi chậm hơn máy cá nhân."""
    sent = client.send_message(BOT_USERNAME, COMMAND)
    sent_time = sent.date

    for attempt in range(6):  # thử tối đa 6 lần, mỗi lần cách nhau vài giây
        time.sleep(WAIT_SECONDS)
        for msg in client.iter_messages(BOT_USERNAME, limit=5):
            if not msg.out and msg.text and msg.date > sent_time:
                return msg.text
        print(f"Chưa có phản hồi, thử lại lần {attempt + 1}...")

    return ""


def parse_vouchers(text: str):
    """
    Tách nhiều mã từ 1 tin nhắn dài (các mã cách nhau bằng dòng gạch ngang ─────)
    Trả về danh sách dict, mỗi dict là 1 mã.
    """
    if not text:
        return []

    blocks = re.split(r"─{3,}", text)
    results = []

    for block in blocks:
        amount_match = re.search(r"Giảm\s*([^\n]+)", block)
        code_match = re.search(r"🏷\s*(\S+)", block)
        used_match = re.search(r"Đã dùng:\s*(\d+)%", block)
        luot_match = re.search(r"Lượt lưu:\s*([^\n]+)", block)
        han_match = re.search(r"Hạn:\s*([^\n]+)", block)
        phi_match = re.search(r"Phí:\s*([\d.,]+)\s*VNĐ", block)

        if not (amount_match and code_match):
            continue  # đoạn này không phải 1 khối mã hợp lệ -> bỏ qua

        con_luot = True
        if luot_match and ("hết" in luot_match.group(1).lower()):
            con_luot = False

        results.append({
            "percent": f"Giảm {amount_match.group(1).strip()}",
            "code": code_match.group(1).strip(),
            "da_dung_percent": int(used_match.group(1)) if used_match else None,
            "con_luot": con_luot,
            "han_dung": han_match.group(1).strip() if han_match else None,
            "phi_vnd": phi_match.group(1).strip() if phi_match else None,
        })

    return results


def main():
    session_string = os.environ.get("TELEGRAM_SESSION")
    session = StringSession(session_string) if session_string else SESSION_NAME

    with TelegramClient(session, API_ID, API_HASH) as client:
        reply_text = get_bot_reply(client)

        if not reply_text:
            print("Không nhận được câu trả lời từ bot. Kiểm tra lại BOT_USERNAME hoặc COMMAND.")
            vouchers = []
        else:
            vouchers = parse_vouchers(reply_text)
            if not vouchers:
                # In ra nội dung để debug nếu không tách được mã nào
                print("--- Nội dung bot trả lời (không tách được mã nào) ---")
                print(reply_text[:1500])

        # Chỉ giữ các mã còn lượt dùng
        vouchers_con_luot = [v for v in vouchers if v.get("con_luot", True)]

        result = {
            "cap_nhat_luc": datetime.now(timezone.utc).isoformat(),
            "vouchers": vouchers_con_luot,
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Đã lưu {len(vouchers_con_luot)} mã (trong tổng {len(vouchers)} mã tìm thấy) vào {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
