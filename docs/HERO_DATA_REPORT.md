# Báo cáo dữ liệu 129 tướng

Ngày đối chiếu: 19/10/2026. Phiên bản bộ dữ liệu: `official-2026.10.15`. Phương pháp chấm: `hero-rating-v1`.

## Kết quả kiểm tra

| Hạng mục | Kết quả |
|---|---:|
| Tướng trong bảng `heroes` | 129 |
| ID duy nhất | 129 |
| Hồ sơ Garena có nguồn xác minh | 129 |
| Kỹ năng chính thức đã lưu | 516 |
| Rating có ít nhất một thuộc tính có bằng chứng | 129 |
| Tướng có ít nhất một matchup đủ ba cặp thuộc tính chung | 115 |
| Hồ sơ phân tích hoàn chỉnh | 0 |
| Hồ sơ phân tích một phần | 129 |
| Hồ sơ còn cần quản trị viên duyệt | 129 |

Các ID gốc được giữ nguyên; ví dụ `Thane=1`, `Alice=2`, `Nakroth=3`. Migration `0002_hero_analysis` chỉ thêm bảng phân tích, không sửa khóa chính của `heroes`.

## Đã có

- Tên, vai trò, ảnh và bốn mô tả kỹ năng của đủ 129 tướng, kèm URL, thời gian lấy và SHA-256 nội dung.
- Điểm thuật toán nullable, giải thích, bằng chứng, độ tin cậy, nguồn gốc và phiên bản phương pháp.
- Search không dấu/tên một phần/alias trên API và component chọn tướng dùng chung.
- Cấu trúc lưu điểm mạnh, điểm yếu, matchup, synergy, power spike, build, nguồn và phiên bản phân tích.

## Chưa được phép coi là hoàn chỉnh

- Garena không công bố đủ 15 thuộc tính chuẩn hóa 0–100. Thuộc tính thiếu bằng chứng được để `null`, không gán 50.
- Điểm yếu riêng, sức mạnh theo ba giai đoạn, build/ngọc/phù hiệu theo bản hiện hành và quan hệ synergy chưa đủ nguồn để tự động xác nhận cho toàn bộ 129 tướng.
- 129 hồ sơ đang ở trạng thái `official_partial_analysis`; tất cả cần quản trị viên hoặc chuyên gia duyệt trước khi đổi thành `complete`.
- 14 tướng chưa có đủ ba cặp thuộc tính chung để tạo matchup; API trả `insufficient` thay vì tự gán điểm.
- Meta win/pick/ban vẫn trống vì chưa có nguồn thống kê có phiên bản và cỡ mẫu hợp lệ.

## Cách tái tạo

```powershell
.\.venv\Scripts\python.exe .\scripts\sync_official_roster.py
.\.venv\Scripts\python.exe .\scripts\sync_official_hero_details.py
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m pytest -q
```
