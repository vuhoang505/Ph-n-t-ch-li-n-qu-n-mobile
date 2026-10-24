# AOV Strategy Open

Nền tảng full-stack phân tích chiến thuật Liên Quân Mobile bằng engine đa tiêu chí có thể giải thích. Giao diện hoàn toàn bằng tiếng Việt, mặc định dark mode và hỗ trợ desktop/mobile.

## Trạng thái hiện tại

- Hoạt động công khai, không yêu cầu đăng ký hoặc đăng nhập: kho tướng, chi tiết/radar, phân tích Draft, tạo đội hình, so sánh khắc chế hai chiều, đề xuất trang bị, chiến thuật theo giai đoạn, hỏi Google trực tiếp, tải ảnh có kiểm tra, lưu yêu thích cục bộ, OpenAPI và rate limiting.
- Meta Analytics không tạo số liệu giả; hiện hiển thị “Chưa có dữ liệu xác thực”.
- Nhận diện ảnh chưa có mô hình đã kiểm định nên yêu cầu xác nhận thủ công, không đoán tên tướng.
- Kho tướng giữ nguyên 129 ID ban đầu; 129/129 tướng có hồ sơ nguồn chính thức và 516 mô tả kỹ năng. Rating Engine phân tích toàn bộ roster nhưng giữ `null` cho thuộc tính chưa đủ bằng chứng, không tự gán điểm trung bình.
- Catalog gameplay hiện có 112 trang bị, 88 ngọc, 9 phép bổ trợ, 4 nhánh và 31 phù hiệu từ Học viện Garena. Build/phối hợp/đối đầu được ghi rõ là kết quả thuật toán suy ra từ dữ liệu nguồn, không phải khuyến nghị chính thức của Garena.

Chi tiết quyết định kỹ thuật nằm tại [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Cài đặt trên Windows

Yêu cầu: Python 3.11+, Node.js 20+.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
```

Script tạo `.venv` trong dự án, không cài thư viện Python toàn cục.

Sao chép `.env.example` thành `.env`, đổi `SECRET_KEY` trước khi triển khai. Mặc định dùng SQLite. Để dùng MySQL:

```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/aov_strategy
```

## Khởi chạy

Terminal 1:

```powershell
.\scripts\run-backend.ps1
```

Terminal 2:

```powershell
.\scripts\run-frontend.ps1
```

Mở `http://localhost:5173`. OpenAPI ở `http://127.0.0.1:8000/docs`.

## Kiểm thử

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Set-Location ..\frontend
npm test
npm run build
```

## Migration và dữ liệu

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Dữ liệu khởi tạo: `data/imports/starter_data.json`. Snapshot đã xác minh nằm tại `official_roster.json`, `official_hero_details.json` và `official_gameplay_catalog.json`. Khi nhập dữ liệu thật, giữ trường `patch_version`, URL nguồn, trạng thái xác minh và không ghi tỷ lệ meta nếu thiếu nguồn/cỡ mẫu.

Đồng bộ lại danh sách và ảnh từ nguồn chính thức:

```powershell
.\.venv\Scripts\python.exe .\scripts\sync_official_roster.py
.\.venv\Scripts\python.exe .\scripts\sync_official_hero_details.py
.\.venv\Scripts\python.exe .\scripts\sync_official_gameplay_catalog.py
.\.venv\Scripts\python.exe .\scripts\audit_hero_data.py
```

Kết quả được lưu tại `data/imports/official_roster.json`. Script chỉ nhập tên, vai trò, ảnh và URL hồ sơ; không tự tạo điểm chiến thuật hoặc số liệu meta.

## Hỏi đáp công khai

Trang “Hỏi Google” tạo liên kết tìm kiếm trực tiếp trên `google.com`, tự thêm tên tướng đã chọn và cụm “Liên Quân Mobile”. Ứng dụng không chạy mô hình AI, không cần API key và không lưu câu hỏi trên máy chủ.

## Production

Frontend: `npm run build`, triển khai thư mục `frontend/dist` lên static hosting và đặt `VITE_API_URL` tới backend. Backend: chạy Uvicorn/Gunicorn phía sau reverse proxy HTTPS, dùng MySQL, thay `SECRET_KEY`, giới hạn CORS và quản lý bí mật ngoài source code.

# Ph-n-t-ch-li-n-qu-n-mobile

