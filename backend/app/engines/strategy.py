from .scoring import composition_analysis


PHASE_PLAYBOOK = {
    "đầu trận": {
        "priority": "Giữ nhịp đi đường, tranh chấp mục tiêu đầu tiên khi có quyền ưu tiên đường.",
        "avoid": "Không ép giao tranh thiếu người hoặc khi các đường chưa đẩy xong.",
        "map": "Cắm tầm nhìn lối vào rừng và giữ thông tin người đi rừng đối phương.",
    },
    "giữa trận": {
        "priority": "Đẩy đồng thời hai đường trước khi tập trung kiểm soát mục tiêu lớn.",
        "avoid": "Không chia đội hình quá xa khi mất thông tin chủ lực đối phương.",
        "map": "Chiếm bụi và cửa ngõ quanh mục tiêu trước thời điểm xuất hiện.",
    },
    "cuối trận": {
        "priority": "Bảo vệ nguồn sát thương chính và chơi quanh sai lầm vị trí của đối phương.",
        "avoid": "Không đổi mạng hỗ trợ lấy chủ lực và không đẩy cao khi thiếu tầm nhìn.",
        "map": "Dọn đường xa trước, sau đó di chuyển cùng nhau qua vùng đã kiểm soát.",
    },
}


def analyze_strategy(allies, enemies, phase: str) -> dict:
    own = composition_analysis(allies)
    opposing = composition_analysis(enemies)
    playbook = PHASE_PLAYBOOK[phase]
    own_engage, enemy_engage = own["scores"]["engage"], opposing["scores"]["engage"]
    own_mobility, enemy_mobility = own["scores"]["mobility"], opposing["scores"]["mobility"]
    engage_delta = own_engage - enemy_engage if own_engage is not None and enemy_engage is not None else None
    mobility_delta = own_mobility - enemy_mobility if own_mobility is not None and enemy_mobility is not None else None
    if engage_delta is not None and engage_delta >= 8:
        condition = "Chủ động mở giao tranh khi đủ người và kỹ năng khống chế chủ chốt sẵn sàng."
    elif mobility_delta is not None and mobility_delta >= 10:
        condition = "Kéo giãn đội hình đối thủ, tạo thế hơn người rồi mới giao tranh."
    elif engage_delta is not None or mobility_delta is not None:
        condition = "Ưu tiên phản giao tranh, buộc đối thủ đi qua điểm hẹp đã kiểm soát."
    else:
        condition = "Chưa đủ dữ liệu cơ động và mở giao tranh; ưu tiên giữ đội hình và xác nhận thông tin trước khi giao tranh."
    statuses = {own["data_status"], opposing["data_status"]}
    status = "insufficient" if "insufficient" in statuses else "partial" if "partial" in statuses else "ok"
    return {
        "phase": phase,
        "priority": playbook["priority"],
        "map_control": playbook["map"],
        "fight_timing": condition,
        "avoid": playbook["avoid"],
        "win_condition": condition,
        "ally_analysis": own,
        "enemy_analysis": opposing,
        "confidence": round(min(0.92, (own["confidence"] + opposing["confidence"]) / 2), 2),
        "status": status,
        "message": (
            "Một số chỉ số chưa có đủ bằng chứng; chiến thuật chỉ dùng các chỉ số đã xác minh."
            if status != "ok" else None
        ),
    }

