import { BookOpen, Check, Copy, Download, Gem, PackageOpen, ShieldCheck, Sparkles } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { HeroPicker } from "../components/HeroPicker";
import { HeroSearchSelect } from "../components/HeroSearchSelect";
import { Button, Card, EmptyState, Select } from "../components/ui";
import { useHeroes } from "../hooks/useHeroes";
import { get, post } from "../services/api";
import type { Hero } from "../types";

// ── Types ─────────────────────────────────────────────────────────────────────
type ItemAttrs = Record<string, number | string>;

type BuildItem = {
  id: number;
  name: string;
  image_url: string | null;
  category: string;
  cost: number | null;
  attributes: ItemAttrs;
  score: number;
  reason: string;
  replace_when: string;
};

type BuildResult = {
  hero: string;
  position: string;
  phase: string;
  threat_profile: { physical: number | null; magic: number | null };
  confidence: number;
  items: BuildItem[];
  status: string;
  message: string | null;
  score_kind: string;
  loadout: {
    status: string;
    summary?: string;
    arcana: { color: string; name: string; image_url: string | null; description: string; level: string | null; count: number }[];
    enchantment: { family: string; entries: { name: string; image_url: string | null; description: string; level: string | null }[] } | null;
    talent: { name: string; image_url: string | null; description: string } | null;
  };
};

type CatalogItem = {
  external_key: string;
  name: string;
  image_url: string | null;
  category: string;
  level: string | null;
  description: string;
  attributes: ItemAttrs;
  source_url: string;
};

type CatalogSection<T> = { section: string; items: T[]; generated_at: string };

export function buildToShareText(result: BuildResult): string {
  const itemLine = result.items.map((item, index) => `${index + 1}. ${item.name}`).join(" → ");
  const runeLine = result.loadout.arcana.map(rune => `${rune.color}: 10× ${rune.name}`).join(" | ");
  const enchantLine = result.loadout.enchantment
    ? `${result.loadout.enchantment.family}: ${result.loadout.enchantment.entries.map(item => item.name).join(" → ")}`
    : "Chưa có";
  return [
    `BUILD ${result.hero.toUpperCase()} · ${result.position} · ${result.phase}`,
    `Trang bị: ${itemLine}`,
    `Bảng ngọc: ${runeLine || "Chưa có"}`,
    `Phù hiệu: ${enchantLine}`,
    `Bổ trợ: ${result.loadout.talent?.name ?? "Chưa có"}`,
    "AOV Strategy · Vũ Huy Hoàng",
  ].join("\n");
}

function wrapCanvasText(context: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth: number, lineHeight: number, maxLines = 2) {
  const words = text.split(" ");
  let line = "";
  let lines = 0;
  for (const word of words) {
    const next = `${line}${line ? " " : ""}${word}`;
    if (context.measureText(next).width > maxWidth && line) {
      context.fillText(line, x, y + lines * lineHeight);
      line = word;
      lines += 1;
      if (lines >= maxLines - 1) break;
    } else line = next;
  }
  if (lines < maxLines) context.fillText(line, x, y + lines * lineHeight);
}

type BuildCardFormat = "landscape" | "portrait";

function loadCanvasImage(url: string | null | undefined): Promise<HTMLImageElement | null> {
  if (!url) return Promise.resolve(null);
  return new Promise(resolve => {
    const image = new Image(); image.crossOrigin = "anonymous";
    image.onload = () => resolve(image); image.onerror = () => resolve(null); image.src = url;
  });
}

async function downloadBuildCard(result: BuildResult, hero: Hero | undefined, format: BuildCardFormat) {
  const canvas = document.createElement("canvas");
  const portrait = format === "portrait";
  canvas.width = portrait ? 1080 : 1600;
  canvas.height = portrait ? 1920 : 900;
  const context = canvas.getContext("2d");
  if (!context) return;
  const width = canvas.width, height = canvas.height, padding = portrait ? 70 : 72;
  const [heroImage, ...assetImages] = await Promise.all([
    loadCanvasImage(hero?.image_url),
    ...result.items.map(item => loadCanvasImage(item.image_url)),
    ...result.loadout.arcana.map(item => loadCanvasImage(item.image_url)),
    ...((result.loadout.enchantment?.entries ?? []).map(item => loadCanvasImage(item.image_url))),
    loadCanvasImage(result.loadout.talent?.image_url),
  ]);
  const gradient = context.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#071426"); gradient.addColorStop(.58, "#101637"); gradient.addColorStop(1, "#27164d");
  context.fillStyle = gradient; context.fillRect(0, 0, width, height);
  if (heroImage) { context.save(); context.globalAlpha = .28; const scale = Math.max(width / heroImage.width, height / heroImage.height); context.drawImage(heroImage, width - heroImage.width * scale, 0, heroImage.width * scale, heroImage.height * scale); context.restore(); }
  context.fillStyle = "rgba(4,11,26,.62)"; context.fillRect(0, 0, width, height);
  context.strokeStyle = "rgba(92,232,255,.38)"; context.lineWidth = 3; context.strokeRect(30, 30, width - 60, height - 60);
  context.fillStyle = "#5ce8ff"; context.font = `700 ${portrait ? 24 : 26}px Segoe UI`; context.fillText("AOV STRATEGY · COMPLETE BUILD", padding, portrait ? 105 : 92);
  context.fillStyle = "#f3f7ff"; context.font = `800 ${portrait ? 68 : 62}px Segoe UI`; context.fillText(result.hero, padding, portrait ? 190 : 165);
  context.fillStyle = "#9caed0"; context.font = `500 ${portrait ? 26 : 24}px Segoe UI`; context.fillText(`${result.position} · ${result.phase}`, padding, portrait ? 235 : 205);
  const iconSize = portrait ? 124 : 118, itemY = portrait ? 330 : 295, gap = portrait ? 22 : 24;
  context.fillStyle = "#a68cff"; context.font = "700 22px Segoe UI"; context.fillText("6 TRANG BỊ CỐT LÕI", padding, itemY - 35);
  result.items.slice(0,6).forEach((item, index) => { const columns = portrait ? 3 : 6, row = Math.floor(index / columns), col = index % columns; const x = padding + col * (iconSize + gap), y = itemY + row * (iconSize + 54); context.fillStyle = "rgba(13,29,53,.92)"; context.fillRect(x,y,iconSize,iconSize); const image = assetImages[index]; if (image) context.drawImage(image,x,y,iconSize,iconSize); context.strokeStyle = "#b794ff"; context.strokeRect(x,y,iconSize,iconSize); context.fillStyle = "#eaf0ff"; context.font = "600 16px Segoe UI"; wrapCanvasText(context,item.name,x,y+iconSize+23,iconSize,18,2); });
  const runeStart = 6, runeY = portrait ? 820 : 520;
  context.fillStyle = "#5ce8ff"; context.font = "700 22px Segoe UI"; context.fillText("BẢNG NGỌC · PHÙ HIỆU · BỔ TRỢ", padding, runeY - 36);
  const loadoutAssets = [...result.loadout.arcana.map((rune,index) => ({ name: `10× ${rune.name}`, image: assetImages[runeStart + index] })), ...((result.loadout.enchantment?.entries ?? []).map((entry,index) => ({ name: entry.name, image: assetImages[runeStart + result.loadout.arcana.length + index] }))), { name: result.loadout.talent?.name ?? "Bổ trợ", image: assetImages[assetImages.length - 1] }];
  loadoutAssets.forEach((asset,index) => { const columns = portrait ? 3 : 7, size = portrait ? 105 : 86, col=index%columns,row=Math.floor(index/columns),x=padding+col*(size+(portrait?32:28)),y=runeY+row*(size+52); context.fillStyle="rgba(10,26,47,.9)"; context.fillRect(x,y,size,size); if(asset.image) context.drawImage(asset.image,x,y,size,size); context.strokeStyle="#55dff5"; context.strokeRect(x,y,size,size); context.fillStyle="#dbeaff"; context.font=`600 ${portrait?15:13}px Segoe UI`; wrapCanvasText(context,asset.name,x,y+size+21,size,17,2); });
  const footerY = height - 75; context.fillStyle = "#7085a8"; context.font = "500 18px Segoe UI"; context.fillText("© Vũ Huy Hoàng · Chỉ dành cho nghiên cứu và học tập", padding, footerY);
  context.textAlign = "right"; context.fillStyle="#5ce8ff"; context.font="700 18px Segoe UI"; context.fillText(portrait ? "STORY · 9:16" : "SOCIAL · 16:9",width-padding,footerY); context.textAlign="left";
  const save = (url: string) => { const link = document.createElement("a"); link.download = `build-${result.hero.toLowerCase().replace(/\s+/g, "-")}.png`; link.href = url; link.click(); };
  canvas.toBlob(blob => { if (!blob) return; const url = URL.createObjectURL(blob); save(url); setTimeout(() => URL.revokeObjectURL(url), 1000); }, "image/png");
}

// ── Helpers ────────────────────────────────────────────────────────────────────
const ATTR_LABEL: Record<string, string> = {
  physical_attack: "Công vật lý",
  magic_power: "Công phép",
  max_health: "Máu",
  armor: "Giáp",
  magic_defense: "Giáp phép",
  attack_speed: "Tốc đánh",
  movement_speed: "Tốc chạy",
  cooldown_reduction: "Giảm hồi chiêu",
  lifesteal: "Hút máu",
  critical_chance: "Chí mạng",
  armor_pierce: "Xuyên giáp",
  magic_pierce: "Xuyên giáp phép",
};

function AttrPills({ attrs }: { attrs: ItemAttrs }) {
  const entries = Object.entries(attrs)
    .filter(([k, v]) => ATTR_LABEL[k] && typeof v === "number" && v > 0)
    .slice(0, 4);
  if (!entries.length) return null;
  return (
    <div className="attr-pills">
      {entries.map(([k, v]) => (
        <span key={k} className="attr-pill">
          <em>{ATTR_LABEL[k]}</em>
          <b>+{typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(0)) : v}</b>
        </span>
      ))}
    </div>
  );
}

function ItemPortrait({ item }: { item: BuildItem | CatalogItem }) {
  const [imgErr, setImgErr] = useState(false);
  if (item.image_url && !imgErr) {
    return (
      <img
        className="item-portrait"
        src={item.image_url}
        alt={item.name}
        onError={() => setImgErr(true)}
      />
    );
  }
  return <div className="item-glyph">{item.name.slice(0, 1)}</div>;
}

// ── Sections ───────────────────────────────────────────────────────────────────
function BuildItemCard({ item, index }: { item: BuildItem; index: number }) {
  return (
    <Card className="build-item">
      <span className="item-order">{index + 1}</span>
      <ItemPortrait item={item} />
      <div>
        <h3>{item.name}</h3>
        <span>{item.category}{item.cost ? ` · ${item.cost} vàng` : ""}</span>
        <AttrPills attrs={item.attributes} />
        <p>{item.reason}</p>
        <small>{item.replace_when}</small>
      </div>
      <b>{item.score}</b>
    </Card>
  );
}

function CatalogSection({
  title,
  section,
  filterFn,
}: {
  title: string;
  section: "runes" | "enchantments" | "talents";
  filterFn?: (item: CatalogItem) => boolean;
}) {
  const { data, isLoading, isError } = useQuery<CatalogSection<CatalogItem>>({
    queryKey: ["catalog", section],
    queryFn: () => get(`/gameplay-catalog?section=${section}`),
    staleTime: 10 * 60 * 1000,
  });

  const items = data?.items.filter(filterFn ?? (() => true)) ?? [];

  if (isLoading) return <p className="muted" style={{ fontSize: 10, padding: "10px 0" }}>Đang tải {title}…</p>;
  if (isError || !items.length) return null;

  return (
    <div className="catalog-section">
      <h4 className="catalog-section-title">{title}</h4>
      <div className="catalog-grid">
        {items.map((item) => (
          <div key={item.external_key} className="catalog-tile" title={item.description}>
            <ItemPortrait item={item} />
            <span>{item.name}</span>
            {item.level && <small>{item.level}</small>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export function BuildPage() {
  const heroes = useHeroes().data?.items ?? [];
  const [heroId, setHeroId] = useState(0);
  const [enemies, setEnemies] = useState<number[]>([]);
  const [position, setPosition] = useState("Rừng");
  const [phase, setPhase] = useState("giữa trận");
  const [playstyle, setPlaystyle] = useState("cân bằng");
  const [tab, setTab] = useState<"build" | "runes" | "enchantments">("build");
  const [shareState, setShareState] = useState<"idle" | "copied" | "exported">("idle");
  const [cardFormat, setCardFormat] = useState<BuildCardFormat>("landscape");

  const mutation = useMutation({
    mutationFn: () =>
      post<BuildResult>("/build/recommend", {
        hero_id: heroId,
        enemy_ids: enemies,
        ally_ids: [],
        position,
        phase,
        playstyle,
      }),
  });

  const result = mutation.data;
  const selectedHero = heroes.find(hero => hero.id === heroId);
  const copyBuild = async () => {
    if (!result) return;
    const text = buildToShareText(result);
    const fallbackCopy = () => {
      const field = document.createElement("textarea"); field.value = text; document.body.appendChild(field); field.select(); document.execCommand("copy"); field.remove();
    };
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else fallbackCopy();
    } catch { fallbackCopy(); }
    setShareState("copied");
  };

  return (
    <div className="page">
      <div className="page-intro">
        <div>
          <span>ADAPTIVE BUILD ENGINE</span>
          <h2>Lên trang bị theo tình huống</h2>
          <p>
            Thứ tự mua được tính từ vai trò, nguồn sát thương đối phương, giai đoạn và phong cách
            chơi. Ngọc và phù hiệu được sắp xếp để bạn lựa chọn nhanh theo từng kịch bản.
          </p>
        </div>
      </div>

      <div className="two-col build-layout">
        {/* ── Form ─────────────────────────────────────────── */}
        <Card className="form-card">
          <h3>
            <PackageOpen /> Dữ liệu trận đấu
          </h3>
          <label>
            Tướng đang sử dụng
            <HeroSearchSelect
              heroes={heroes}
              value={heroId}
              onChange={setHeroId}
              excludeIds={enemies}
              module="build"
            />
          </label>
          <HeroPicker
            heroes={heroes.filter((h) => h.id !== heroId)}
            selected={enemies}
            onChange={setEnemies}
            label="ĐỘI HÌNH ĐỐI PHƯƠNG"
            module="build"
          />
          <label>
            Vị trí
            <Select value={position} onChange={(e) => setPosition(e.target.value)}>
              {["Caesar", "Rừng", "Giữa", "Rồng", "Trợ thủ"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </Select>
          </label>
          <label>
            Giai đoạn
            <Select value={phase} onChange={(e) => setPhase(e.target.value)}>
              {["đầu trận", "giữa trận", "cuối trận"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </Select>
          </label>
          <label>
            Phong cách
            <Select value={playstyle} onChange={(e) => setPlaystyle(e.target.value)}>
              {["cân bằng", "tấn công", "dồn sát thương", "an toàn", "chống chịu"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </Select>
          </label>
          <Button disabled={!heroId || mutation.isPending} onClick={() => { setTab("build"); setShareState("idle"); mutation.mutate(); }}>
            <Sparkles size={16} /> Tạo bộ trang bị
          </Button>
        </Card>

        {/* ── Results ──────────────────────────────────────── */}
        <div>
          {result ? (
            <>
              <div className="build-result-head"><div><span>COMPLETE BUILD</span><h3>{result.hero} · {result.position}</h3></div><div className="build-export-actions"><div className="build-format-switch"><button type="button" className={cardFormat === "landscape" ? "active" : ""} onClick={() => setCardFormat("landscape")}>16:9</button><button type="button" className={cardFormat === "portrait" ? "active" : ""} onClick={() => setCardFormat("portrait")}>9:16</button></div><button type="button" onClick={copyBuild}>{shareState === "copied" ? <Check /> : <Copy />} {shareState === "copied" ? "Đã sao chép" : "Sao chép"}</button><button type="button" onClick={async () => { await downloadBuildCard(result, selectedHero, cardFormat); setShareState("exported"); }}><Download /> {shareState === "exported" ? "Đã tải ảnh" : "Tải ảnh trang bị"}</button></div></div>
              {/* Threat bar */}
              <Card className="threat-card">
                <span>
                  Áp lực vật lý <b>{result.threat_profile.physical ?? "—"}</b>
                </span>
                <span>
                  Áp lực phép <b>{result.threat_profile.magic ?? "—"}</b>
                </span>
                <small>Điểm tổng hợp thuộc tính, không phải phần trăm sát thương.</small>
              </Card>

              {/* Tab switcher */}
              <div className="build-tabs">
                <button
                  className={`build-tab${tab === "build" ? " active" : ""}`}
                  onClick={() => setTab("build")}
                >
                  <PackageOpen size={13} /> Build hoàn chỉnh
                </button>
                <button
                  className={`build-tab${tab === "runes" ? " active" : ""}`}
                  onClick={() => setTab("runes")}
                >
                  <BookOpen size={13} /> Ngọc
                </button>
                <button
                  className={`build-tab${tab === "enchantments" ? " active" : ""}`}
                  onClick={() => setTab("enchantments")}
                >
                  ✦ Phù hiệu
                </button>
              </div>

              {/* Items tab */}
              {tab === "build" && (
                <div className="complete-build">
                  <div className="build-list">{result.items.map((item, index) => <BuildItemCard key={item.id} item={item} index={index} />)}</div>
                  <Card className="recommended-loadout"><header><Sparkles /><div><b>Bộ thiết lập đề xuất</b><span>{result.loadout.summary}</span></div></header><div className="loadout-recommend-grid"><section><h4><Gem /> Bảng ngọc</h4>{result.loadout.arcana.map(rune => <article key={rune.color}>{rune.image_url ? <img src={rune.image_url} alt="" /> : <i>{rune.color.slice(0, 1)}</i>}<span><b>{rune.color} · {rune.count} viên</b><small>{rune.name}</small><em>{rune.description}</em></span></article>)}</section><section><h4><ShieldCheck /> Phù hiệu</h4><strong>{result.loadout.enchantment?.family ?? "Chưa có"}</strong>{result.loadout.enchantment?.entries.map(entry => <article key={entry.name}>{entry.image_url ? <img src={entry.image_url} alt="" /> : <i>{entry.level?.slice(-1) ?? "✦"}</i>}<span><b>{entry.level}</b><small>{entry.name}</small></span></article>)}</section><section><h4><Sparkles /> Bổ trợ</h4>{result.loadout.talent ? <article className="talent-pick">{result.loadout.talent.image_url ? <img src={result.loadout.talent.image_url} alt="" /> : <i>✦</i>}<span><b>{result.loadout.talent.name}</b><em>{result.loadout.talent.description}</em></span></article> : <p className="muted">Chưa có đề xuất.</p>}</section></div></Card>
                </div>
              )}

              {/* Runes tab */}
              {tab === "runes" && (
                <Card className="catalog-card">
                  <p className="catalog-intro">
                    Chọn bộ ngọc phù hợp với vai trò, nhịp trận và phong cách của bạn.
                  </p>
                  <CatalogSection title="Ngọc Đỏ" section="runes" filterFn={(r) => r.category === "Đỏ"} />
                  <CatalogSection title="Ngọc Xanh" section="runes" filterFn={(r) => r.category === "Xanh"} />
                  <CatalogSection title="Ngọc Tím" section="runes" filterFn={(r) => r.category === "Tím"} />
                </Card>
              )}

              {/* Enchantments tab */}
              {tab === "enchantments" && (
                <Card className="catalog-card">
                  <p className="catalog-intro">
                    Kết hợp phù hiệu và phép bổ trợ theo chiến thuật và lối chơi.
                  </p>
                  <CatalogSection title="Phù hiệu" section="enchantments" />
                  <CatalogSection title="Phụ trợ" section="talents" />
                </Card>
              )}

            </>
          ) : (
            <EmptyState
              title="Chưa có bộ trang bị"
              description="Chọn tướng và bối cảnh trận đấu để engine xếp hạng trang bị, ngọc và phù hiệu."
            />
          )}
        </div>
      </div>
    </div>
  );
}
