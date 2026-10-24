# Kiến trúc AOV Strategy AI

Hệ thống dùng kiến trúc modular monolith để chạy đơn giản nhưng vẫn tách ranh giới rõ ràng:

```text
React UI → REST API / Pydantic → Application services → Scoring engines
                                      ↓                    ↓
                              SQLAlchemy repositories  Explainability
                                      ↓
                             SQLite / MySQL + nguồn dữ liệu
```

## Nguyên tắc dữ liệu

- `MetaStatistic` chỉ được trả về khi `verified=true`, có nguồn và cỡ mẫu.
- Điểm thuộc tính 0–100 là đánh giá chiến thuật dùng cho thuật toán, không phải tỷ lệ thắng.
- Mọi tướng và trang bị mang `patch_version`; mọi nguồn có trạng thái xác minh và thời gian truy xuất.
- Bộ `bootstrap-2026.10` chỉ là dữ liệu khởi tạo biên soạn thủ công, được hiển thị rõ là chờ đối chiếu.
- `official_roster.json` được tạo trực tiếp từ Học viện Liên Quân. Hồ sơ chỉ có roster/ảnh mang trạng thái `official_roster_only` và bị loại khỏi các engine cho đến khi có thuộc tính chiến thuật đã duyệt.

## Recommendation Engine

Draft Engine tổng hợp bốn thành phần chuẩn hóa: đối kháng 30%, phối hợp 27%, chiến thuật 25%, vai trò 18%. Composition Engine tính vector trung bình của 10 năng lực và phát hiện khoảng trống. Build Engine xếp hạng trang bị bằng loại sát thương đối phương, vai trò và phong cách chơi. Tất cả kết quả trả về `score_kind=algorithmic` cùng độ tin cậy.

Các engine là hàm thuần theo dữ liệu đầu vào, nên có thể thay thành mô hình ML sau này mà không đổi hợp đồng API.

