# Customer Care Bot

Bot tự động: mỗi sáng 8h (giờ VN), quét Google Sheet khách hàng, phát hiện ai có
sinh nhật / Tết Tây / Tết Âm rơi vào hôm nay hoặc ngày mai, rồi gửi lời chúc
soạn sẵn về Telegram để bạn copy sang Zalo gửi khách.

Phase 2 (hiện tại): Gemini sinh lời chúc, template cố định làm fallback. Khi
thiếu `GEMINI_API_KEY`, tắt `USE_AI`, hoặc Gemini lỗi/quá tải, bot tự dùng lại
template Phase 1 — không bao giờ im lặng.

## Setup từ đầu

### 1. Tạo Google Sheet

Tạo 1 Google Sheet mới với 2 tab, đúng tên và đúng thứ tự cột:

**Tab `customers`:**

| name         | gender | birth_date | age_group | note | active | phone      |
| ------------ | ------ | ---------- | --------- | ---- | ------ | ---------- |
| Nguyễn Văn A | Nam    | 15/06/1990 |           |      | TRUE   | 0901234567 |
| Trần Thị B   | Nữ     | 01/01/1985 |           |      | TRUE   |            |

- `birth_date`: định dạng `dd/mm/yyyy`, luôn có đủ năm sinh.
- `active`: `TRUE` để bot xử lý, `FALSE` để bỏ qua.
- `gender`, `age_group`, `note`, `phone`: có thể để trống nếu không cần.
- `phone` (tuỳ chọn): nếu có sẽ hiện ở tiêu đề tin để nhân viên tra nhanh
  (chạm số để copy). Đặt cột ở đâu cũng được, miễn header đúng tên `phone`.

**Tab `sent_log`:** chỉ cần dòng tiêu đề, bot sẽ tự ghi thêm:

| date_sent | customer_name | event_type | notify_type | year |
| --------- | ------------- | ---------- | ----------- | ---- |

Copy `SHEET_ID` từ URL của Sheet:
`https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

### 2. Tạo Google Service Account (để bot đọc/ghi Sheet)

1. Vào [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo project mới (hoặc dùng project có sẵn).
3. Vào **APIs & Services → Library**, tìm và bật **Google Sheets API**.
4. Vào **APIs & Services → Credentials → Create Credentials → Service Account**.
   Đặt tên tuỳ ý, bấm qua các bước còn lại (không cần gán role đặc biệt).
5. Vào service account vừa tạo → tab **Keys → Add Key → Create new key → JSON**.
   File JSON sẽ tự tải về máy — **đây là bí mật, không commit lên Git**.
6. Mở file JSON, tìm giá trị `client_email` (dạng
   `xxx@xxx.iam.gserviceaccount.com`).
7. Quay lại Google Sheet đã tạo ở bước 1 → bấm **Share** → dán `client_email`
   đó vào, cấp quyền **Editor** → Send.

### 3. Tạo Telegram Bot

1. Mở Telegram, tìm **@BotFather**, gửi lệnh `/newbot`.
2. Đặt tên và username cho bot theo hướng dẫn.
3. BotFather trả về **token** dạng `123456789:ABC-...` — đây là
   `TELEGRAM_BOT_TOKEN`.
4. Mở chat với bot vừa tạo, gửi bất kỳ tin nhắn nào (ví dụ "hi") để bot nhận
   diện được chat.
5. Lấy `TELEGRAM_CHAT_ID` bằng cách mở trình duyệt, truy cập:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (thay `<TOKEN>` bằng token thật). Tìm trường `"chat":{"id": ...}` trong kết
   quả JSON — đó là `TELEGRAM_CHAT_ID`. Lưu ý: bot chỉ gửi được cho người **đã
   nhắn bot trước** (bấm Start), và `chat.id` là id của người gửi tin đó (không
   phải của chủ token).
   - **Gửi cho nhiều người** (vd nhân viên + bạn để theo dõi): đặt nhiều id ngăn
     cách bằng dấu phẩy, ví dụ `TELEGRAM_CHAT_ID=111111,222222`. Mỗi người nhận
     đều phải tự nhắn bot trước.

### 4. Tạo Gemini API key (để AI sinh lời chúc)

1. Vào [Google AI Studio → API keys](https://aistudio.google.com/apikey).
2. Bấm **Create API key** (chọn hoặc tạo 1 Google Cloud project). Key có dạng
   `AIza...` — **đây là bí mật, không commit lên Git**.
3. Gói miễn phí đủ dùng cho lượng khách nhỏ (mỗi ngày bot chỉ gọi API cho vài
   sự kiện). Nếu chưa muốn dùng AI, có thể bỏ trống và đặt `USE_AI=0` — bot sẽ
   dùng template cố định.

### 5. Cấu hình `.env`

```bash
cp .env.example .env
```

Điền vào `.env`:

```
SHEET_ID=<sheet id từ bước 1>
TELEGRAM_BOT_TOKEN=<token từ bước 3>
TELEGRAM_CHAT_ID=<chat id từ bước 3>
GOOGLE_CREDENTIALS_FILE=<đường dẫn tới file JSON từ bước 2>
GEMINI_API_KEY=<api key từ bước 4>
USE_AI=1
DRY_RUN=1
```

> Khi chạy local, dùng `GOOGLE_CREDENTIALS_FILE` trỏ tới file JSON. Khi chạy
> trên GitHub Actions, dùng `GOOGLE_CREDENTIALS_JSON` (dán nguyên nội dung file
> JSON vào 1 GitHub Secret).

### 6. Chạy thử

```bash
pip install -r requirements.txt
pytest tests/                        # unit test, không cần credentials

python -m src.main                   # đọc .env tự động (nhờ python-dotenv)
                                      # DRY_RUN=1 trong .env → chỉ in ra,
                                      # KHÔNG gửi Telegram / KHÔNG ghi log
```

Với `DRY_RUN=1`, bot **vẫn gọi Gemini** để bạn xem trước lời chúc AI thật (chỉ
chặn bước gửi Telegram + ghi log). Nếu thấy đúng danh sách và lời chúc ưng ý →
sửa `DRY_RUN=0` trong `.env` để gửi thật, rồi chạy lại `python -m src.main`.

## Triển khai tự động (GitHub Actions)

1. Push code lên GitHub repo (đừng commit `.env` hay file JSON credentials —
   đã có trong `.gitignore`).
2. Vào repo → **Settings → Secrets and variables → Actions → New repository
   secret**, thêm 5 secret:
   - `SHEET_ID`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GOOGLE_CREDENTIALS_JSON` (dán nguyên nội dung file JSON, 1 dòng)
   - `GEMINI_API_KEY` (key từ bước 4; bỏ qua nếu chạy không dùng AI)
3. Vào tab **Actions** → chọn workflow **Daily Customer Care Bot** → **Run
   workflow** để chạy thử thủ công.
4. Nếu ổn, workflow sẽ tự chạy mỗi ngày lúc 8h sáng giờ VN (cron
   `0 1 * * *` UTC).

## Cấu trúc code

```
src/
  config.py      # đọc env + helper giờ VN: today_vn(), tomorrow_vn(); cờ DRY_RUN
  lunar.py       # thuật toán Hồ Ngọc Đức (tz=7); dùng nhất: tet_solar_date(year)
  sheets.py      # auth service account; load_customers(), load_sent_log(), append_sent_rows()
  events.py      # quét sự kiện T-1/T-0 + Tết toàn cục; lọc theo sent_log; trả list Event
  salutation.py  # (tuổi, giới tính) -> nhóm xưng hô (gọi khách / mình xưng)
  gemini.py      # Phase 2: gọi Gemini (REST) sinh 2–3 lời chúc; lỗi -> None (fallback)
  messages.py    # build_message: ưu tiên AI, fallback template; đóng khung Telegram <pre>
  telegram.py    # sendMessage (1 tin/khách), bọc lời chúc trong <pre> để copy
  main.py        # orchestrator: đọc -> quét -> render -> gửi -> ghi log
tests/                                # unit test, không cần credentials thật
.github/workflows/daily.yml           # cron '0 1 * * *' (= 8h VN) + workflow_dispatch
```

Xem `CLAUDE.md` để biết đầy đủ quy ước, ràng buộc, và tiến độ dự án.
