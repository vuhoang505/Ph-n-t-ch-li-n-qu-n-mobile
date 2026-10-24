import { BarChart3, Camera, CheckCircle2, ImagePlus, RefreshCw, ScanLine } from "lucide-react";
import { ChangeEvent, useEffect, useState } from "react";
import { Button, Card, EmptyState } from "../components/ui";
import { api } from "../services/api";

type VisionResult = {
  status: "analyzed";
  filename: string;
  image: { format: string; width: number; height: number; aspect_ratio: number };
  scene: { key: string; label: string; confidence: number };
  quality: string;
  metrics: { brightness: number; contrast: number; saturation: number; edge_density: number; dominant_tone: string };
  regions: { name: string; x: number; y: number; width: number; height: number }[];
  recommendations: string[];
  message: string;
};

export function VisionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState<VisionResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0] ?? null;
    setFile(next); setResult(null); setError("");
    setPreview(next ? URL.createObjectURL(next) : "");
  };
  const analyze = async () => {
    if (!file) return;
    setLoading(true); setError("");
    const form = new FormData(); form.append("file", file);
    try { setResult(await api<VisionResult>("/vision/analyze", { method: "POST", body: form })); }
    catch (e) { setError(e instanceof Error ? e.message : "Không thể xử lý ảnh"); }
    finally { setLoading(false); }
  };
  const reset = () => { setFile(null); setResult(null); setError(""); setPreview(""); };

  return <div className="page">
    <div className="page-intro"><div><span>VISION WORKSPACE</span><h2>Phân tích ảnh trận đấu</h2><p>Tải ảnh để đọc kích thước, chất lượng, bố cục và nhận gợi ý kiểm tra thế trận ngay trong trang.</p></div></div>
    <div className="two-col vision-layout">
      <Card className="upload-card">
        <label className="upload-zone"><input type="file" accept="image/png,image/jpeg,image/webp" onChange={choose} /><ImagePlus /><b>Chọn ảnh chụp màn hình</b><span>PNG, JPEG hoặc WebP · tối đa 8 MB</span></label>
        {preview && <div className="preview vision-preview"><img src={preview} alt="Ảnh trận đấu đã tải" /><ScanLine />{result?.regions.map(region => <i key={region.name} title={region.name} style={{ left: `${region.x * 100}%`, top: `${region.y * 100}%`, width: `${region.width * 100}%`, height: `${region.height * 100}%` }} />)}</div>}
        <div className="vision-actions"><Button disabled={!file || loading} onClick={analyze}><Camera size={17} /> {loading ? "Đang đọc ảnh..." : "Phân tích ảnh"}</Button>{file && <button type="button" onClick={reset}><RefreshCw size={15} /> Chọn lại</button>}</div>
        {error && <div className="error-banner">{error}</div>}
      </Card>
      <Card className="vision-result">{result ? <div className="vision-analysis">
        <header><CheckCircle2 /><div><small>ĐÃ PHÂN TÍCH</small><h3>{result.scene.label}</h3><p>{result.message}</p></div><strong>{Math.round(result.scene.confidence * 100)}%</strong></header>
        <div className="vision-facts"><span><small>KÍCH THƯỚC</small><b>{result.image.width}×{result.image.height}</b></span><span><small>ĐỊNH DẠNG</small><b>{result.image.format}</b></span><span><small>CHẤT LƯỢNG</small><b>{result.quality}</b></span><span><small>TÔNG MÀU</small><b>{result.metrics.dominant_tone}</b></span></div>
        <div className="vision-metrics"><div><span>Độ sáng</span><i><em style={{ width: `${result.metrics.brightness}%` }} /></i><b>{result.metrics.brightness}</b></div><div><span>Tương phản</span><i><em style={{ width: `${result.metrics.contrast}%` }} /></i><b>{result.metrics.contrast}</b></div><div><span>Bão hòa</span><i><em style={{ width: `${result.metrics.saturation}%` }} /></i><b>{result.metrics.saturation}</b></div></div>
        <section><h4><BarChart3 /> Gợi ý đọc thế trận</h4><ol>{result.recommendations.map(item => <li key={item}>{item}</li>)}</ol></section>
      </div> : <EmptyState title="Chưa có ảnh phân tích" description="Tải ảnh cấm chọn, đội hình, bảng điểm hoặc ảnh trong trận để bắt đầu." />}</Card>
    </div>
  </div>;
}
