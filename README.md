# 🔍 OmniTrace – OSINT & Lead Generation Chrome Extension

> **Cào dữ liệu toàn bộ mạng xã hội → Tạo Email → Xác thực → Xuất CRM**
>
> Extension trình duyệt kết hợp OSINT đa nền tảng – thu thập thông tin công khai từ **500+ mạng xã hội** (không chỉ LinkedIn), tự động tạo danh sách email ứng viên, xác thực qua SMTP, và xuất dữ liệu ra CSV / Notion.

---

## 📁 Cấu trúc dự án

```
OmniTrace-Extensions/
├── frontend/                  # Chrome Extension (React + Vite + TypeScript)
│   ├── manifest.json          # Manifest V3 – content_scripts + background
│   ├── vite.config.ts         # Vite + @crxjs/vite-plugin
│   ├── src/
│   │   ├── App.tsx            # Popup UI chính (OSINT trace tool)
│   │   ├── App.css            # Toàn bộ styling
│   │   ├── content/index.ts   # Content Script (inject vào LinkedIn)
│   │   ├── background/index.ts# Service Worker
│   │   └── main.tsx           # React entry
│   └── public/                # icon.png, favicon.svg
│
├── backend/                   # FastAPI OSINT API Server
│   ├── main.py                # Endpoints: /api/health, /api/trace, /api/trace/image
│   ├── requirements.txt       # fastapi, uvicorn, httpx, holehe, maigret, pillow…
│   ├── tracers/
│   │   ├── models.py          # Pydantic: Result, Profile
│   │   ├── username_lookup.py # Maigret – quét 500 trang theo username
│   │   ├── email_lookup.py    # holehe + Gravatar – check email đã đăng ký ở đâu
│   │   ├── name_lookup.py     # GitHub search + link tìm người trên MXH
│   │   └── image_lookup.py    # EXIF + reverse image (Yandex, Google Lens, TinEye)
│   └── test_modules.py
│
└── README.md                  # ← Bạn đang đọc file này
```

---

## 🗺️ Lộ trình phát triển (Roadmap) – Đánh giá trạng thái

### Phase 1: Local MVP – Extension cào dữ liệu thô (2 tuần)

> 📌 **Scope mở rộng:** Roadmap gốc chỉ cào LinkedIn. Dự án đã nâng cấp thành **OSINT đa nền tảng** – cào thông tin trên toàn bộ mạng xã hội của mục tiêu, không giới hạn ở LinkedIn.

| # | Task | Trạng thái | Ghi chú |
|---|------|:----------:|---------|
| 1.1 | Setup React + Vite Extension (Manifest V3) | ✅ Xong | `@crxjs/vite-plugin`, React 19, TypeScript |
| 1.2 | Content Script inject vào trang web | ✅ Xong | `content/index.ts` cào DOM LinkedIn, gửi dữ liệu về popup |
| 1.3 | **Cào thông tin đa nền tảng** (mở rộng so với roadmap) | ✅ Xong | Backend cào **500+ trang** qua Maigret (username), **120+ trang** qua holehe (email), GitHub, Gravatar, reverse image search |
| 1.4 | Popup UI hiển thị kết quả trace | ✅ Xong | UI hoàn chỉnh: 4 chế độ (Username/Email/Họ tên/Hình ảnh), badge trạng thái, filter, profile card |
| 1.5 | Nút xuất dữ liệu (JSON) | ✅ Xong | Export JSON hoạt động. |
| 1.6 | Nút xuất dữ liệu ra file **.CSV** | ✅ Xong | Đã bổ sung export CSV bao gồm cả OSINT & LinkedIn |

**Kết luận Phase 1:** 🟢 **100% hoàn thành** – Đã vượt xa scope LinkedIn-only. Hệ thống OSINT đa nền tảng hoạt động. Đã tích hợp cào dữ liệu LinkedIn trực tiếp từ trang.

---

### Phase 2: Bộ não OSINT Backend (2 tuần)

| # | Task | Trạng thái | Ghi chú |
|---|------|:----------:|---------|
| 2.1 | Code FastAPI Backend | ✅ Xong | `main.py` – 3 endpoints, CORS, Pydantic models |
| 2.2 | Module tra cứu Username (500+ trang) | ✅ Xong | Maigret – quét song song, trích xuất profile, phân loại confirmed/unverified |
| 2.3 | Module tra cứu Email (120+ trang) | ✅ Xong | holehe + Gravatar – phát hiện email đăng ký ở đâu, trích avatar/bio/linked accounts |
| 2.4 | Module tra cứu Họ tên | ✅ Xong | GitHub user search + link tìm người trên Facebook, LinkedIn, X, TikTok, YouTube |
| 2.5 | Module tra cứu Hình ảnh | ✅ Xong | EXIF metadata + GPS + reverse image (Google Lens, Yandex, Bing, TinEye) |
| 2.6 | Tích hợp Extension ↔ Backend | ✅ Xong | Extension gọi Backend qua `fetch()`, health check tự động, hiển thị kết quả realtime |
| 2.7 | Thuật toán tạo danh sách Email (tên + công ty) | ✅ Xong | `backend/tracers/email_generator.py` – tạo pattern email phổ biến |
| 2.8 | SMTP ping xác thực Email tồn tại | ✅ Xong | `backend/tracers/smtp_verifier.py` – kết nối MX record, RCPT TO |

**Kết luận Phase 2:** 🟢 **100% hoàn thành** – Backend OSINT đa nền tảng hoàn chỉnh và mạnh mẽ. 

---

### Phase 3: Hệ thống Cloud & Tích hợp (2 tuần)

| # | Task | Trạng thái | Ghi chú |
|---|------|:----------:|---------|
| 3.1 | Database trên Supabase | ❌ **Chưa làm** | Không có schema, config, hay Supabase client |
| 3.2 | Đăng ký / Đăng nhập người dùng | ❌ **Chưa làm** | Extension không có auth flow |
| 3.3 | Export → Notion (người dùng dán API Key) | ❌ **Chưa làm** | Chưa có Notion integration |

**Kết luận Phase 3:** 🔴 **0% hoàn thành**

---

### Phase 4: Thương mại hóa & Launch (1 tuần)

| # | Task | Trạng thái | Ghi chú |
|---|------|:----------:|---------|
| 4.1 | Landing Page giới thiệu OmniTrace | ❌ **Chưa làm** | |
| 4.2 | Đóng gói Extension, submit Chrome Web Store | ❌ **Chưa làm** | Cần trả $5 cho Google Developer account |

**Kết luận Phase 4:** 🔴 **0% hoàn thành**

---

## 📊 Tổng kết trạng thái

```
Phase 1 ████████████████████ 100%   (OSINT đa nền tảng xong, CSV + LinkedIn scraper xong)
Phase 2 ████████████████████ 100%   (Backend hoàn chỉnh, Email Gen + SMTP xong)
Phase 3 ░░░░░░░░░░░░░░░░░░░░   0%   (chưa bắt đầu)
Phase 4 ░░░░░░░░░░░░░░░░░░░░   0%   (chưa bắt đầu)
───────────────────────────────────
TỔNG    ████████████░░░░░░░░  ~50%
```

### 💡 Nhận xét: Dự án đã **mở rộng vượt roadmap gốc**

Roadmap ban đầu chỉ yêu cầu cào **LinkedIn** (Tên, Chức vụ, Công ty). Dự án đã nâng cấp thành hệ thống **OSINT toàn diện** – cào thông tin trên **500+ mạng xã hội** thông qua username, email, họ tên, và cả hình ảnh (reverse image search + EXIF). Đây là hướng phát triển tốt hơn vì:

- **Phạm vi rộng hơn:** Không chỉ LinkedIn mà tất cả MXH
- **Đa phương thức:** 4 cách tra cứu (username, email, tên, ảnh)
- **Dữ liệu phong phú:** Profile, avatar, bio, location, linked accounts

**Việc còn lại** để hoàn tất roadmap: Bắt đầu triển khai Phase 3 (Supabase + Notion) & Phase 4 (Landing Page + Submit Web Store).

---

## 🚀 Việc cần làm tiếp theo (theo thứ tự ưu tiên)

### ✏️ Sprint tiếp theo – Triển khai Phase 3

- [ ] Setup Supabase project + schema (users, leads, scraped_profiles)
- [ ] Auth flow trong Extension (Supabase Auth)
- [ ] Notion export (nhận Notion API Key từ user, đẩy dữ liệu)

### ✏️ Phase 4

- [ ] Landing page (HTML/CSS hoặc Next.js)
- [ ] Đóng gói production build, submit Chrome Web Store

---

## 🛠️ Cài đặt & Chạy thử

### Frontend (Chrome Extension)

```bash
cd frontend
npm install
npm run dev
```

Mở `chrome://extensions` → bật Developer Mode → Load unpacked → chọn thư mục `frontend/dist`

### Backend (FastAPI OSINT Server)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔧 Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Extension | React 19 · TypeScript · Vite 8 · @crxjs/vite-plugin · Manifest V3 |
| Backend | Python · FastAPI · Pydantic · httpx |
| OSINT Engines | Maigret (500 sites) · holehe (120+ sites) · Gravatar · EXIF/Pillow · Reverse Image Search |
| Planned | Supabase (DB + Auth) · Notion API · SMTP Verification |

---

## 📜 Giấy phép

Dự án này chỉ được sử dụng cho **mục đích hợp pháp**. Người dùng tự chịu trách nhiệm về cách sử dụng dữ liệu thu thập được.
