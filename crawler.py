# ==========================================================
#  CRAWLER: đọc mã giảm giá từ kênh Telegram, lưu ra data.json
#  Dành cho người mới — đọc kỹ từng bước hướng dẫn bên dưới
# ==========================================================
#
# BƯỚC 1 — Lấy API_ID và API_HASH (làm 1 lần duy nhất):
#   1. Vào https://my.telegram.org -> đăng nhập bằng số điện thoại của bạn
#   2. Chọn "API development tools"
#   3. Điền App title: "voucher-crawler", Short name: "voucher"
#   4. Bạn sẽ nhận được API_ID (số) và API_HASH (chuỗi ký tự)
#   5. Dán 2 giá trị đó vào bên dưới (dòng API_ID = ... và API_HASH = ...)
#
# BƯỚC 2 — Cài thư viện cần thiết (chạy trong terminal/cmd):
#   pip install telethon
#
# BƯỚC 3 — Điền tên kênh cần đọc (CHANNEL_USERNAME bên dưới).
#   Nếu kênh không có username công khai, dùng đúng tên hiển thị
#   của group/kênh (Telethon vẫn tìm được nếu tài khoản bạn đã ở trong đó).
#
# BƯỚC 4 — Chạy lần đầu: python crawler.py
#   Lần đầu chạy sẽ hỏi số điện thoại + mã xác nhận Telegram gửi về máy bạn.
#   Sau lần đầu, chương trình tự lưu phiên đăng nhập (file voucher_session.session)
#   nên các lần sau KHÔNG cần đăng nhập lại.
#
# ==========================================================

import json
import os
import re
from datetime import datetime, timezone
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# ---------- CẤU HÌNH ----------
# API_ID và API_HASH KHÔNG được viết thẳng vào đây nữa (vì file này sẽ
# đăng công khai lên GitHub). Chúng được đọc từ Secret khi chạy tự động,
# hoặc bạn có thể tạm điền trực tiếp CHỈ KHI chạy thử trên máy mình
# (nhớ xóa lại trước khi tải file lên GitHub).
API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
CHANNEL_USERNAME = "sfast_main_bot"  # <-- tên kênh/group cần đọc, cái này để public được, không nhạy cảm
# -------------------------------------------------

SESSION_NAME = "voucher_session"
OUTPUT_FILE = "data.json"
MESSAGE_LIMIT = 30   # số tin nhắn gần nhất sẽ quét mỗi lần chạy


def parse_message(text: str):
    """
    Tách thông tin mã giảm giá từ 1 tin nhắn.
    Trả về dict nếu tin nhắn đúng định dạng mã, ngược lại trả về None.
    Chỉnh regex ở đây nếu định dạng tin nhắn trong kênh của bạn khác đi.
    """
    if not text:
        return None

    # Ví dụ dòng cần bắt: "💰 Giảm 100k (Mã 337)"
    amount_match = re.search(r"Giảm\s*([^\(\n]+)\(Mã\s*(\d+)\)", text)
    # Ví dụ dòng cần bắt: "🏷 NEWUSERD4K2PA"
    code_match = re.search(r"🏷\s*([A-Za-z0-9]+)", text)
    # Ví dụ dòng cần bắt: "Đã dùng: 16%"
    used_match = re.search(r"Đã dùng:\s*(\d+)%", text)

    if not (amount_match and code_match):
        return None  # tin nhắn này không phải tin đăng mã -> bỏ qua

    return {
        "percent": f"Giảm {amount_match.group(1).strip()}",
        "ma_so": amount_match.group(2),
        "code": code_match.group(1),
        "da_dung_percent": int(used_match.group(1)) if used_match else None,
    }


def main():
    # Khi chạy trên GitHub Actions, dùng biến môi trường TELEGRAM_SESSION
    # (chuỗi tạo ra từ generate_session.py) thay vì file .session
    session_string = os.environ.get("TELEGRAM_SESSION")
    session = StringSession(session_string) if session_string else SESSION_NAME

    with TelegramClient(session, API_ID, API_HASH) as client:
        vouchers = []
        for message in client.iter_messages(CHANNEL_USERNAME, limit=MESSAGE_LIMIT):
            parsed = parse_message(message.text)
            if parsed:
                parsed["thoi_gian"] = message.date.astimezone(
                    timezone.utc
                ).isoformat()
                vouchers.append(parsed)

        result = {
            "cap_nhat_luc": datetime.now(timezone.utc).isoformat(),
            "vouchers": vouchers,
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"Đã lưu {len(vouchers)} mã vào {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
