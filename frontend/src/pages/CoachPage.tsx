import { GitBranch, Send, Sparkles } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { HeroPicker } from "../components/HeroPicker";
import { Button, Card, Input } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import type { Hero } from "../types";

type AnswerNode = { title: string; text: string; children: string[] };
export type AnswerTree = { summary: string; nodes: AnswerNode[] };

const metricLabels: Record<string, string> = {
  physical_damage: "sát thương vật lý", magic_damage: "sát thương phép", durability: "chống chịu",
  crowd_control: "khống chế", mobility: "cơ động", engage: "mở giao tranh",
  protection: "bảo vệ chủ lực", split_push: "đẩy lẻ", wave_clear: "dọn lính", objective_control: "kiểm soát mục tiêu",
};

export function buildAnswerTree(question: string, selected: Hero[]): AnswerTree {
  const normalized = question.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").toLowerCase();
  const averages = Object.keys(metricLabels).map(key => {
    const values = selected.map(hero => hero.attributes[key as keyof Hero["attributes"]]).filter((value): value is number => value != null);
    return { key, value: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null };
  });
  const known = averages.filter((row): row is { key: string; value: number } => row.value != null).sort((a, b) => b.value - a.value);
  const strongest = known.slice(0, 2).map(row => metricLabels[row.key]);
  const weakest = [...known].reverse().slice(0, 2).map(row => metricLabels[row.key]);
  const names = selected.map(hero => hero.name);
  let actions = ["Kiểm tra vị trí còn thiếu trước khi khóa lựa chọn.", "Giữ kỹ năng khống chế cho mục tiêu cơ động.", "Đồng bộ thời điểm giao tranh với mục tiêu lớn."];
  if (normalized.includes("khac che")) actions = ["So sánh cơ động của mục tiêu với lượng khống chế đang có.", "Ưu tiên tiếp cận từ góc khuất thay vì truy đuổi trực diện.", "Điều chỉnh trang bị phòng thủ theo nguồn sát thương chính."];
  if (normalized.includes("trang bi") || normalized.includes("build") || normalized.includes("len do")) actions = ["Mở công cụ Lên trang bị và chọn đúng tướng đang dùng.", "Thêm đội hình địch để xác định áp lực vật lý và phép.", "Thay món tình huống khi nguồn sát thương chủ đạo thay đổi."];
  if (normalized.includes("cam") || normalized.includes("draft") || normalized.includes("chon")) actions = ["Loại toàn bộ tướng đã cấm khỏi tập ứng viên.", "Khóa vai trò còn thiếu trước khi tối ưu điểm phối hợp.", "Đối chiếu lựa chọn cuối với nguồn sát thương hai đội."];
  return {
    summary: selected.length
      ? `Với ${names.join(", ")}, hướng xử lý nên dựa trên dữ liệu đội hình hiện có và điều kiện giao tranh trong câu hỏi.`
      : "Chưa chọn tướng cụ thể, nên câu trả lời tập trung vào quy trình ra quyết định có thể áp dụng ngay.",
    nodes: [
      { title: "Đọc dữ liệu", text: selected.length ? `Đang phân tích ${selected.length} tướng đã chọn.` : "Chưa có ngữ cảnh tướng.", children: strongest.length ? [`Điểm nổi bật: ${strongest.join(", ")}.`, `Điểm cần bù: ${weakest.join(", ")}.`] : ["Chọn tướng để bổ sung chỉ số đội hình."] },
      { title: "Kết luận", text: question.trim(), children: actions },
      { title: "Kế hoạch hành động", text: "Chuyển kết luận thành ba việc có thể thực hiện ngay trong trận.", children: ["Chốt điều kiện mở giao tranh trước khi di chuyển.", "Giữ lại kỹ năng quan trọng cho mục tiêu ưu tiên.", "Đánh giá lại đội hình sau mỗi lượt cấm/chọn."] },
    ],
  };
}

export function CoachPage() {
  const heroes = useHeroes().data?.items ?? [];
  const [heroIds, setHeroIds] = useState<number[]>([]);
  const [input, setInput] = useState("");
  const [conversation, setConversation] = useState<{ question: string; answer: AnswerTree }[]>([]);
  const selected = useMemo(() => heroes.filter(hero => heroIds.includes(hero.id)), [heroIds, heroes]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const question = input.trim();
    if (!question) return;
    setConversation(previous => [...previous, { question, answer: buildAnswerTree(question, selected) }]);
    setInput("");
  };

  return <div className="page coach-page">
    <div className="page-intro"><div><span>TACTICAL Q&A</span><h2>Trợ lý chiến thuật</h2><p>Nhập câu hỏi để nhận cây trả lời trực quan theo tướng và bối cảnh đội hình đang chọn.</p></div></div>
    <div className="coach-layout">
      <Card className="coach-context"><h3><Sparkles /> Ngữ cảnh tướng</h3><HeroPicker heroes={heroes} selected={heroIds} onChange={setHeroIds} max={10} label="TƯỚNG LIÊN QUAN" /><div className="prompt-suggestions"><button onClick={() => setInput("Đội hình này đang thiếu gì?")}>Đội hình thiếu gì?</button><button onClick={() => setInput("Nên giao tranh hay đẩy lẻ?")}>Giao tranh hay đẩy lẻ?</button><button onClick={() => setInput("Làm sao khắc chế tướng cơ động?")}>Khắc chế cơ động?</button></div></Card>
      <div className="answer-workspace">
        <div className="answer-feed">{conversation.length ? conversation.map((turn, turnIndex) => <div className="answer-turn" key={`${turn.question}-${turnIndex}`}><div className="question-bubble">{turn.question}</div><Card className="answer-tree"><header><GitBranch /><div><small>PHÂN TÍCH CHIẾN THUẬT</small><b>{turn.answer.summary}</b></div></header><div className="tree-nodes">{turn.answer.nodes.map((node, index) => <section key={node.title} style={{ animationDelay: `${index * 80}ms` }}><i>{index + 1}</i><div><h3>{node.title}</h3><p>{node.text}</p><ul>{node.children.map(child => <li key={child}>{child}</li>)}</ul></div></section>)}</div></Card></div>) : <Card className="answer-empty"><GitBranch /><h3>Cây trả lời sẽ xuất hiện tại đây</h3><p>Chọn tướng nếu cần ngữ cảnh cụ thể, hoặc đặt câu hỏi ngay.</p></Card>}</div>
        <form className="answer-composer" onSubmit={submit}><Input value={input} onChange={event => setInput(event.target.value)} placeholder="Hỏi về đội hình, khắc chế, trang bị hoặc draft..." /><Button disabled={!input.trim()}><Send size={16} /> Gửi câu hỏi</Button></form>
      </div>
    </div>
  </div>;
}
