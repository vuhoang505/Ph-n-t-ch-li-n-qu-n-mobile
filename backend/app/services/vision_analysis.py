from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError


def analyze_match_image(content: bytes, filename: str | None) -> dict:
    """Perform deterministic visual inspection without inventing hero names."""
    try:
        with Image.open(BytesIO(content)) as source:
            image_format = (source.format or "unknown").upper()
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Tệp không phải ảnh hợp lệ hoặc đã bị hỏng.") from exc

    width, height = image.size
    if width < 320 or height < 180:
        raise ValueError("Ảnh quá nhỏ để phân tích; cần tối thiểu 320×180 px.")
    if width * height > 40_000_000:
        raise ValueError("Ảnh vượt quá giới hạn 40 megapixel.")

    sample = image.copy()
    sample.thumbnail((480, 480))
    stat = ImageStat.Stat(sample)
    red, green, blue = (round(value, 1) for value in stat.mean)
    brightness = round((red * 0.2126 + green * 0.7152 + blue * 0.0722) / 255 * 100, 1)
    contrast = round(sum(stat.stddev) / 3 / 128 * 100, 1)
    hsv = sample.convert("HSV")
    saturation = round(ImageStat.Stat(hsv).mean[1] / 255 * 100, 1)
    edges = sample.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_density = round(ImageStat.Stat(edges).mean[0] / 255 * 100, 1)
    aspect_ratio = round(width / height, 2)

    if aspect_ratio >= 1.55 and edge_density >= 7:
        scene = "in_match"
        label = "Ảnh trong trận đấu"
        confidence = min(0.9, 0.58 + edge_density / 100)
        recommendations = [
            "Đối chiếu minimap trước khi quyết định giao tranh hoặc ăn mục tiêu lớn.",
            "Kiểm tra chênh lệch vàng, cấp độ và số người đang hiện trên bản đồ.",
            "Cắt riêng khu vực bảng điểm nếu cần đọc chính xác trang bị và KDA.",
        ]
    elif aspect_ratio >= 1.4:
        scene = "draft_or_scoreboard"
        label = "Màn hình cấm chọn hoặc bảng điểm"
        confidence = 0.66
        recommendations = [
            "Dùng ảnh rõ toàn bộ hai đội để đánh giá cân bằng sát thương và khống chế.",
            "Nếu là bảng điểm, ưu tiên kiểm tra trang bị khắc chế nguồn sát thương dẫn trước.",
            "Xác nhận thủ công tên tướng trước khi dùng kết quả cho Draft hoặc Đội hình.",
        ]
    elif aspect_ratio < 0.9:
        scene = "portrait_crop"
        label = "Ảnh dọc hoặc ảnh đã cắt"
        confidence = 0.72
        recommendations = [
            "Tải ảnh ngang toàn màn hình để hệ thống đọc bố cục trận đấu tốt hơn.",
            "Không cắt mất minimap, bảng KDA hoặc thanh trạng thái hai đội.",
        ]
    else:
        scene = "general_screenshot"
        label = "Ảnh chụp giao diện tổng quát"
        confidence = 0.55
        recommendations = ["Cung cấp ảnh toàn màn hình, rõ chữ và không bị che để tăng độ tin cậy."]

    tone = "lạnh" if blue > red * 1.08 else "ấm" if red > blue * 1.08 else "cân bằng"
    quality = "tốt" if min(width, height) >= 720 and contrast >= 20 else "đủ dùng" if min(width, height) >= 480 else "thấp"
    return {
        "status": "analyzed",
        "filename": filename or "image",
        "image": {"format": image_format, "width": width, "height": height, "aspect_ratio": aspect_ratio},
        "scene": {"key": scene, "label": label, "confidence": round(confidence, 2)},
        "quality": quality,
        "metrics": {
            "brightness": brightness, "contrast": contrast, "saturation": saturation,
            "edge_density": edge_density, "dominant_tone": tone,
        },
        "regions": [
            {"name": "Trạng thái hai đội", "x": 0.28, "y": 0.0, "width": 0.44, "height": 0.16},
            {"name": "Khu vực giao tranh", "x": 0.2, "y": 0.16, "width": 0.6, "height": 0.68},
            {"name": "Minimap", "x": 0.0, "y": 0.64, "width": 0.24, "height": 0.36},
        ],
        "recommendations": recommendations,
        "message": "Ảnh đã được đọc và phân tích bố cục thành công. Tên tướng cần được xác nhận khi ảnh không đủ rõ.",
    }
