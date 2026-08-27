// Thin client for the FastAPI backend (SPEC §16). The dashboard never talks to
// Postgres; everything goes through here.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type TopicOption = {
  topic_id: number;
  code: string;
  unit: string;
  name: string;
};

export type MappingView = {
  id: number;
  source_chunk_id: number;
  topic_id: number | null;
  topic_code: string | null;
  topic_name: string | null;
  is_primary: boolean;
  content_type: string;
  difficulty: number | null;
  confidence: number;
  mapping_status: string;
  rationale: string | null;
  model: string | null;
  prompt_version: string | null;
};

export type ReviewItemView = {
  id: number;
  item_type: string;
  status: string;
  risk: number;
  confidence: number | null;
  title: string;
  topic_id: number | null;
  source_document_id: number | null;
  created_at: string;
  audit_sample: boolean;
  chunk_heading: string | null;
  chunk_text: string | null;
  chunk_latex: string | null;
  chunk_stem: string | null;
  mapping: MappingView | null;
  secondaries: MappingView[];
  candidates: TopicOption[];
};

export type Calibration = {
  resolved: number;
  pending: number;
  target: number;
  recommended_threshold: number | null;
  notes: string[];
  bands: {
    lo: number;
    hi: number;
    n: number;
    agree: number;
    disagree: number;
    audit: number;
    agreement: number | null;
  }[];
};

export type QueueStats = {
  open_total: number;
  by_type: Record<string, number>;
  mappings_by_status: Record<string, number>;
  unmapped_chunks: number;
  batchable_groups: number;
};

export type DecisionResult = {
  ok: boolean;
  stats: QueueStats;
  next: ReviewItemView | null;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (res.status === 204) return null as T;
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  queue: () => req<QueueStats>("/review/queue"),
  next: (exclude: number[] = []) =>
    req<ReviewItemView | null>(
      `/review/next${exclude.length ? `?exclude=${exclude.join(",")}` : ""}`,
    ),
  decide: (
    id: number,
    body: {
      reviewer: string;
      decision: "APPROVE" | "REJECT" | "EDIT" | "PROMOTE";
      reason_code?: string;
      note?: string;
      edit?: Record<string, unknown>;
    },
  ) =>
    req<DecisionResult>(`/review/${id}/decision`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  batches: () =>
    req<
      {
        topic_id: number | null;
        source_document_id: number | null;
        item_ids: number[];
        min_confidence: number;
      }[]
    >("/review/batches"),
  batchApprove: (item_ids: number[], reviewer: string) =>
    req<DecisionResult>("/review/batch-approve", {
      method: "POST",
      body: JSON.stringify({ reviewer, item_ids }),
    }),
  calibration: () => req<Calibration>("/review/calibration"),
  curriculum: () =>
    req<
      {
        id: number;
        code: string;
        name: string;
        topics: {
          id: number;
          code: string | null;
          name: string;
          level: string;
          parent_id: number | null;
          mapped_chunks: number;
          also_tests: number;
          approved_chunks: number;
          exercises: number;
        }[];
      }[]
    >("/curriculum"),
  sources: () =>
    req<
      {
        id: number;
        file_ref: string;
        session_code: string | null;
        paper_version: string | null;
        extraction_status: string;
        page_count: number | null;
        chunks: number;
        exercises: number;
        figures: number;
        mappings_by_status: Record<string, number>;
      }[]
    >("/sources"),
  sourceChunks: (id: number) =>
    req<
      {
        id: number;
        order_index: number;
        heading: string | null;
        content_type: string;
        text: string;
        confidence: number | null;
        mapping: MappingView | null;
      }[]
    >(`/sources/${id}/chunks`),
};

export const REASON_CODES = [
  "WRONG_TOPIC",
  "WRONG_CONTENT_TYPE",
  "NOT_CURRICULUM",
  "AMBIGUOUS",
  "LOW_QUALITY_SOURCE",
  "OTHER",
] as const;
