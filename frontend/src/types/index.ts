export type Attributes = {
  physical_damage: number | null; magic_damage: number | null; durability: number | null; crowd_control: number | null;
  mobility: number | null; engage: number | null; protection: number | null; split_push: number | null;
  wave_clear: number | null; objective_control: number | null;
};

export type HeroEngineModule = "composition" | "draft" | "team" | "counter" | "build" | "strategy" | "coach";

export type HeroReadiness = {
  modules?: Partial<Record<HeroEngineModule, boolean>>;
  source?: string;
  confidence?: number;
  known_metrics?: string[];
  missing_metrics?: string[];
  method_version?: string;
};

export type Hero = {
  id: number; slug: string; name: string; image_url: string | null; damage_type: string;
  positions: string[]; power_phase: string; difficulty: number; strengths: string[];
  weaknesses: string[]; patch_version: string; roles: string[]; attributes: Attributes;
  profile_status: "tactical_profile" | "official_roster_only" | "official_partial_analysis" | "official_source_only" | "complete";
  aliases: string[]; data_confidence: number;
  /** Backend-owned readiness flag. Undefined means the UI must not claim readiness. */
  engine_ready?: boolean;
  readiness?: HeroReadiness;
};

export type RatingScores = Record<string, number | null>;
export type HeroAnalysisDetail = {
  hero: Hero;
  analysis: null | { damage_type: string | null; range_type: string | null; special_mechanics: string[]; data_status: string; confidence: number; method_version: string; patch_version: string };
  skills: { id: number; name: string; type: string; description: string; order: number }[];
  skill_priority: { primary: null | { order: number; name: string; label: string }; secondary: null | { order: number; name: string }; ultimate: null | { order: number; name: string; levels: number[] }; levels: { level: number; skill_order: number; skill_name: string; rank: number }[]; advice: string; kind?: string };
  combos: { name: string; steps: { type: "skill" | "attack"; order?: number; label: string }[]; tip: string }[];
  base_stats: { kind: string; label: string; confidence: number; rows: { key: string; label: string; level_1: number; level_15: number; unit: string }[] };
  gameplay_tips: { phase: string; score: number | null; title: string; advice: string }[];
  ratings: null | { scores: RatingScores; explanations: Record<string, string>; evidence: Record<string, string[]>; confidence: number; provenance: string; method_version: string; patch_version: string; score_kind: "algorithmic" };
  tier: null | { tier: "S" | "A" | "B" | "C"; score: number; kind: "algorithmic"; label: string };
  strengths: { title: string; explanation: string; evidence: string[]; confidence: number; provenance: string }[];
  weaknesses: { title: string; explanation: string; evidence: string[]; confidence: number; provenance: string }[];
  power_spikes: { phase: string; score: number | null; analysis: { explanation?: string }; confidence: number; provenance: string }[];
};

export type Composition = {
  size: number; scores: Attributes; missing: string[]; damage_balance: string;
  dominant_phase: string; confidence: number; score_kind: "algorithmic";
};

export type DraftRecommendation = {
  hero: Hero; fit_score: number; counter_score: number | null; synergy_score: number | null;
  strategy_score: number | null; role_score: number; confidence: number;
  advantages: string[]; risks: string[]; explanation: string;
};

