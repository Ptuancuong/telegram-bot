# CLAUDE.md

Hướng dẫn cho Claude Code khi làm việc trong dự án này.

## Dự án là gì

Customer care bot đơn giản: mỗi sáng 8h (giờ VN), quét Google Sheet khách hàng,
phát hiện ai có **sinh nhật / Tết Tây / Tết Âm** rơi vào **hôm nay (T-0)** hoặc
**ngày mai (T-1)**, rồi gửi về **Telegram** của người phụ trách — mỗi khách 1 tin
kèm **2–3 lời chúc** soạn sẵn (trong code block để chạm-copy, dán sang Zalo gửi
khách). Có chống gửi trùng. Chạy tự động bằng **GitHub Actions cron**.

**Persona/văn phong lời chúc**: nhân viên ngân hàng chăm sóc khách mình phụ
trách — lịch sự, chân thành, đủ nghiêm túc mà không cứng nhắc, KHÔNG sến súa,
hạn chế emoji (≤1/câu). Áp dụng cho cả prompt Gemini (`gemini.py`) lẫn template
fallback (`messages.py`).

Nguồn yêu cầu gốc: `Workflow_tạo_customer_care_bot_đơn_giản.docx`.

## Trạng thái: Phase 2 HOÀN TẤT

- **Phase 1 (XONG)**: template lời chúc cố định, verify end-to-end trên production.
- **Phase 2 (XONG)**: Gemini sinh lời chúc, template làm fallback.
  - Toàn bộ logic AI ở `src/gemini.py` (REST + `requests`, không SDK ngoài).
    `generate_wishes()` trả `None` ở mọi lỗi (tắt cờ, thiếu key, network, quota,
    output rỗng) → `messages.build_message` rơi về template. Bot không im lặng.
  - `messages.py`: `build_message` ưu tiên AI rồi fallback; tách `_template_wishes`
    (Phase 1) + `_wrap_telegram` (đóng khung + escape HTML dùng chung).
  - Cấu hình mới ở `config.py`: `GEMINI_API_KEY`, `GEMINI_MODEL`
    (mặc định `gemini-3.1-flash-lite`), `USE_AI` (mặc định bật).
  - Model mặc định cũ `gemini-2.5-flash` bị chặn với user mới → dùng
    **`gemini-3.1-flash-lite`** (rẻ/nhanh, tiếng Việt tốt).
  - Ranh giới giữ nguyên: đừng trộn logic AI vào module khác ngoài `gemini.py`.
  - Bảo mật: key đi qua header `x-goog-api-key` (không để trong URL) tránh lộ
    qua chuỗi lỗi HTTP in ra log Actions.
  - **Verify end-to-end trên production (2026-07-14)**: chạy GitHub Actions
    (workflow_dispatch) → Gemini sinh lời chúc → gửi Telegram thật, người dùng
    xác nhận nhận được tin. Văn phong "nhân viên ngân hàng" đã chốt.
  - Phase 3 (nếu có sau này) chưa định nghĩa — chỉ làm khi người dùng yêu cầu rõ.

## Tech stack

Python 3.11 · `gspread` + `google-auth` (Google Sheet) · `requests` (Telegram API) ·
`zoneinfo` + `tzdata` (giờ VN, **không dùng pytz**) · thuật toán âm lịch **tự viết**
(Hồ Ngọc Đức, UTC+7 — **không dùng thư viện âm lịch ngoài**) · GitHub Actions cron.

## Cấu trúc code

```
src/
  config.py      # đọc env + helper giờ VN: today_vn(), tomorrow_vn(); cờ DRY_RUN
  lunar.py       # thuật toán Hồ Ngọc Đức (tz=7); dùng nhất: tet_solar_date(year)
  sheets.py      # auth service account; load_customers(), load_sent_log(), append_sent_rows()
  events.py      # quét sự kiện T-1/T-0 + Tết toàn cục; lọc theo sent_log; trả list Event
  salutation.py  # (tuổi, giới tính) -> nhóm xưng hô (gọi khách / mình xưng)
  messages.py    # template engine: chào + nội dung theo dịp + đuôi; random 2–3 biến thể
  telegram.py    # sendMessage (1 tin/khách), bọc lời chúc trong <pre> để copy
  main.py        # orchestrator: đọc -> quét -> render -> gửi -> ghi log
tests/
  test_lunar.py  # kiểm âm lịch vs ngày Tết đã biết
  test_events.py # T-1/T-0, biên 31/12, dedup
.github/workflows/daily.yml   # cron '0 1 * * *' (= 8h VN) + workflow_dispatch
```

## Quy ước & ràng buộc

- **Múi giờ**: mọi mốc thời gian tính theo `Asia/Ho_Chi_Minh`. Không dùng
  `datetime.now()` trần — dùng `today_vn()` / `tomorrow_vn()` trong `config.py`.
- **Khoá chống trùng** (sent_log): `(name, event_type, notify_type, year)`.
  - `event_type` ∈ `birthday | tet_duong | tet_am`
  - `notify_type` ∈ `T-1 | T-0`
  - `year` = năm **dương lịch** của sự kiện.
- **birth_date**: định dạng `dd/mm/yyyy`, luôn đủ năm (chốt với người dùng). Tuổi =
  năm hiện tại − năm sinh.
- **Xưng hô** (theo tuổi): `<35` gọi "em" / mình xưng "anh"; `35–60` gọi
  "anh"(nam)/"chị"(nữ) / xưng "em"; `>60` gọi "chú"(nam)/"cô"(nữ) / xưng "cháu".
- **Tết Tây**: T-0 = 1/1, T-1 = 31/12. **Tết Âm**: convert mùng 1 âm → dương qua
  `tet_solar_date()`. Tết Tây/Âm áp dụng cho **mọi** khách `active`.
- **Bí mật**: không bao giờ commit `.env` / file credentials JSON. Khi cần demo
  dữ liệu, dùng giá trị giả.

## Cấu trúc Google Sheet

- Tab `customers`: `name | gender | birth_date | age_group | note | active`
  (chỉ xử lý dòng `active` = TRUE). Cột **`phone`** (tuỳ chọn) nếu có sẽ hiện ở
  tiêu đề tin, bọc `<code>` cho chạm-copy. gspread map theo tên cột nên `phone`
  đặt ở đâu cũng được, miễn header đúng tên.
- Tab `sent_log`: `date_sent | customer_name | event_type | notify_type | year`.

## Biến môi trường (xem `.env.example`)

`SHEET_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GOOGLE_CREDENTIALS_JSON`
(hoặc `GOOGLE_CREDENTIALS_FILE` khi chạy local), `DRY_RUN`.

## Lệnh thường dùng

```bash
pip install -r requirements.txt
pytest tests/                        # chạy unit test
DRY_RUN=1 python -m src.main         # chạy thử: in ra, KHÔNG gửi Telegram/ghi log
python -m src.main                   # chạy thật
```

> Windows PowerShell: đặt env bằng `$env:DRY_RUN=1` trước khi chạy, không dùng cú
> pháp `VAR=value cmd`.

## Khi sửa code, lưu ý

- `DRY_RUN=1` phải **không** gọi Telegram và **không** ghi `sent_log` (chỉ in ra).
- Tết Âm cần kiểm cả `tet_solar_date(today.year)` và năm kế tiếp để an toàn biên
  cuối tháng 12 → đầu tháng 1.
- Escape HTML khi nhét `{name}` / nội dung vào tin Telegram (`parse_mode=HTML`).
- Nếu đụng tới sinh lời chúc, giữ ranh giới Phase 1/Phase 2: template ở `messages.py`,
  đừng trộn logic AI vào các module khác.

## Tiến độ Phase 1 (cập nhật sau mỗi milestone)

> Đây là checklist sống. Phiên mới: đọc mục này để biết đang ở đâu, rồi
> `ls src/` + `pytest` để xác nhận thực tế (code/test là sự thật cuối cùng).
> Sau khi hoàn tất một mục, **tick `[x]` và ghi 1 dòng ghi chú** nếu có.

**Milestone A — Lõi logic thuần (không cần credentials):**

- [x] `requirements.txt`, `.gitignore`, `.env.example` (skeleton) — _đã có_
- [x] `src/config.py`
- [x] `src/lunar.py`
- [x] `src/salutation.py`
- [x] `src/events.py`
- [x] `src/messages.py`
- [x] `tests/test_lunar.py`, `tests/test_events.py` — _mở rộng thêm
      test_config.py, test_salutation.py, test_events_extra.py,
      test_messages_extra.py, test_telegram.py, test_main.py_
- [x] `pytest` xanh hết — _148 passed_

**Milestone B — I/O tích hợp (cần Google Sheet + Telegram bot):**

- [x] `src/sheets.py`
- [x] `src/telegram.py`
- [x] `src/main.py`
- [x] Chạy `DRY_RUN=1` thấy đúng danh sách tin — _verify với Sheet thật (67
      khách active), phát hiện đúng 1 sự kiện birthday, xưng hô + template +
      DRY_RUN gate đều đúng_

**Milestone C — Đóng gói & tự động hóa:**

- [x] `.github/workflows/daily.yml`
- [x] `README.md` (checklist setup từ đầu)
- [x] Chạy thử trên GitHub Actions (workflow_dispatch) thành công — _real run
      trên repo Ptuancuong/telegram-bot: 67 khách, 1 sự kiện (NGUYEN THI HONG
      LIEN, birthday, T-0, 14/07/2026), gửi Telegram thật + ghi sent_log,
      người dùng xác nhận nhận được tin_

## Phase 1: HOÀN TẤT

> Toàn bộ 3 milestone đã xong, verify end-to-end trên production (Google
> Sheet thật + Telegram thật + GitHub Actions thật). Các sự cố đã gặp và xử
> lý trong quá trình làm, để tham khảo nếu tái diễn:
>
> - Code đã qua code-reviewer (fix 1 blocking: template injection qua tên
>   khách) và qa-tester (fix 1 bug thật: sai ký tự "Tỵ" cho năm Rắn).
> - Thêm `python-dotenv` để `.env` tự nạp (trước đó phải set env var qua
>   shell thủ công).
> - Dữ liệu thật ban đầu có `birth_date` sai định dạng (dán nhầm cột kiểu Mỹ
>   m/d/yyyy) — người dùng tự sửa tay, verify lại sạch 100% bằng script kiểm
>   tra 2 lớp (parse-fail + ambiguous day/month swap).
> - GitHub Secrets (SHEET_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) bị dính
>   newline thừa khi copy-paste → gspread 404 SpreadsheetNotFound. Debug bằng
>   step in độ dài secret (không lộ giá trị). Fix tận gốc: `config.py` giờ
>   `.strip()` toàn bộ env var thay vì yêu cầu copy-paste cẩn thận.
>
> Phase 2 (Gemini sinh lời chúc) — xem mục "Trạng thái" đầu file, chưa làm,
> chỉ bắt đầu khi người dùng yêu cầu rõ.
> Milestone C còn thiếu chạy thử GitHub Actions (workflow_dispatch) — cần
> push code lên GitHub + set 4 secrets trước.
