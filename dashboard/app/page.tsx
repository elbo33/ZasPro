"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  REASON_CODES,
  type QueueStats,
  type ReviewItemView,
  type KnowledgeItemView,
} from "./lib/api";

type Mode = "view" | "reject" | "edit" | "promote";

function Stats({ s }: { s: QueueStats | null }) {
  if (!s) return null;
  const t = s.by_type;
  return (
    <div className="statbar">
      <div className="stat">
        <b>{s.open_total}</b>
        <span>open</span>
      </div>
      {Object.entries(t)
        .filter(([, n]) => n > 0)
        .map(([k, n]) => (
          <div className="stat" key={k}>
            <b>{n}</b>
            <span>{k.toLowerCase().replace(/_/g, " ")}</span>
          </div>
        ))}
      <div className="stat">
        <b>{s.mappings_by_status.AI_SUGGESTED ?? 0}</b>
        <span>auto-suggested (not queued)</span>
      </div>
      <div className="stat">
        <b>{s.mappings_by_status.APPROVED ?? 0}</b>
        <span>approved</span>
      </div>
      <div className="stat">
        <b>{s.unmapped_chunks}</b>
        <span>unmapped chunks</span>
      </div>
    </div>
  );
}

const KIND_ORDER = [
  "concept",
  "formula",
  "method",
  "example",
  "objective",
  "misconception",
];

function KnowledgeCard({
  item,
  sel,
}: {
  item: ReviewItemView;
  sel: number;
}) {
  const k = item.knowledge;
  if (!k) return <p className="muted">no spec</p>;
  const items = [...k.items].sort(
    (a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind),
  );
  return (
    <div>
      <div className="row">
        <span className="pill">KNOWLEDGE_SPEC</span>
        <span className="pill mono">{k.requirement_codes.join(", ")}</span>
        {Object.entries(k.counts).map(([kind, n]) => (
          <span className="pill" key={kind}>
            {n} {kind}
          </span>
        ))}
        <span className="muted mono">
          {k.model ?? "stub"} · {k.prompt_version}
        </span>
        {k.exported_at && <span className="pill good">exported</span>}
      </div>

      <h2 style={{ marginBottom: 4 }}>
        <span className="mono">{k.slug}</span> — {k.name}
      </h2>
      {k.scope && (
        <p className="muted" style={{ marginTop: 0 }}>
          {k.scope}
        </p>
      )}

      <div style={{ marginTop: 10 }}>
        {items.map((it, i) => (
          <KRow key={`${it.kind}:${it.id}`} it={it} active={i === sel} />
        ))}
      </div>
    </div>
  );
}

function KRow({ it, active }: { it: KnowledgeItemView; active: boolean }) {
  const rejected = it.status === "REJECTED";
  const approved = it.status === "APPROVED";
  return (
    <div
      className="chunk"
      style={{
        margin: "6px 0",
        padding: "8px 12px",
        opacity: rejected ? 0.45 : 1,
        borderLeft: active
          ? "3px solid var(--accent)"
          : "3px solid transparent",
        textDecoration: rejected ? "line-through" : "none",
      }}
    >
      <div className="row">
        <span className="pill">{it.kind}</span>
        {rejected && <span className="pill bad">rejected</span>}
        {approved && <span className="pill good">approved</span>}
      </div>
      <div style={{ marginTop: 4 }}>
        <b>{it.title}</b>
        {it.detail && (
          <>
            <br />
            <span className="muted">{it.detail}</span>
          </>
        )}
        {it.extra && (
          <>
            <br />
            <span className="muted">{it.extra}</span>
          </>
        )}
      </div>
    </div>
  );
}

export default function ReviewQueuePage() {
  const [item, setItem] = useState<ReviewItemView | null>(null);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [mode, setMode] = useState<Mode>("view");
  const [sel, setSel] = useState(0);
  const [ksSel, setKsSel] = useState(0);
  const [skipped, setSkipped] = useState<number[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const reviewer = useRef("reviewer");
  const busy = useRef(false);

  const isKnowledge = item?.item_type === "KNOWLEDGE_SPEC";
  const kItems = item?.knowledge?.items ?? [];

  useEffect(() => {
    try {
      reviewer.current =
        window.localStorage.getItem("zaspro.reviewer") || "reviewer";
    } catch {
      /* ignore */
    }
  }, []);

  const refresh = useCallback(async (skip: number[]) => {
    const [nextItem, qStats] = await Promise.all([api.next(skip), api.queue()]);
    setItem(nextItem);
    setStats(qStats);
    setMode("view");
    setSel(0);
    setKsSel(0);
  }, []);

  useEffect(() => {
    refresh([])
      .catch((e) => setErr(String(e)))
      .finally(() => setReady(true));
  }, [refresh]);

  const applyResult = useCallback(
    (r: { stats: QueueStats; next: ReviewItemView | null }) => {
      setStats(r.stats);
      setItem(r.next);
      setMode("view");
      setSel(0);
      setKsSel(0);
    },
    [],
  );

  const decide = useCallback(
    async (
      body: Omit<Parameters<typeof api.decide>[1], "reviewer">,
      after?: string,
    ) => {
      if (!item || busy.current) return;
      busy.current = true;
      setErr(null);
      setMsg(null);
      try {
        const r = await api.decide(item.id, {
          reviewer: reviewer.current,
          ...body,
        });
        applyResult(r);
        if (after) setMsg(after);
      } catch (e) {
        setErr(String(e));
      } finally {
        busy.current = false;
      }
    },
    [item, applyResult],
  );

  // per-item reject toggle on a knowledge card — stays on the card
  const toggleReject = useCallback(async () => {
    if (!item || !item.knowledge || busy.current) return;
    const it = kItems[ksSel];
    if (!it) return;
    busy.current = true;
    setErr(null);
    try {
      const key: [string, number] = [it.kind, it.id];
      const edit =
        it.status === "REJECTED"
          ? { unreject_items: [key] }
          : { reject_items: [key] };
      await api.decide(item.id, {
        reviewer: reviewer.current,
        decision: "EDIT",
        edit,
      });
      const fresh = await api.knowledgeSpec(
        item.knowledge?.section_id as number,
      );
      setItem({ ...item, knowledge: fresh });
    } catch (e) {
      setErr(String(e));
    } finally {
      busy.current = false;
    }
  }, [item, kItems, ksSel]);

  const approveAndExport = useCallback(async () => {
    if (!item || busy.current || !isKnowledge) return;
    busy.current = true;
    setErr(null);
    setMsg(null);
    try {
      const sectionId = item.knowledge?.section_id as number;
      await api.decide(item.id, {
        reviewer: reviewer.current,
        decision: "APPROVE",
      });
      const ex = await api.exportKnowledge(sectionId, reviewer.current);
      const [nextItem, qStats] = await Promise.all([api.next([]), api.queue()]);
      setItem(nextItem);
      setStats(qStats);
      setMode("view");
      setSel(0);
      setKsSel(0);
      setMsg(ex.ok ? `approved & exported -> ${ex.path}` : `approved; export failed: ${ex.error}`);
    } catch (e) {
      setErr(String(e));
    } finally {
      busy.current = false;
    }
  }, [item, isKnowledge]);

  const skip = useCallback(async () => {
    if (!item) return;
    const next = [...skipped, item.id];
    setSkipped(next);
    setErr(null);
    setMsg(null);
    try {
      await refresh(next);
    } catch (e) {
      setErr(String(e));
    }
  }, [item, skipped, refresh]);

  const batch = useCallback(async () => {
    if (!item || busy.current) return;
    busy.current = true;
    setErr(null);
    try {
      const groups = await api.batches();
      const g = groups.find((x) => x.item_ids.includes(item.id));
      if (!g) {
        setErr("current item is not part of a batchable group");
        return;
      }
      const r = await api.batchApprove(g.item_ids, reviewer.current);
      applyResult(r);
      setMsg(`batch-approved ${g.item_ids.length} items`);
    } catch (e) {
      setErr(String(e));
    } finally {
      busy.current = false;
    }
  }, [item, applyResult]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const cands = item?.candidates ?? [];

      if (mode === "reject") {
        if (e.key === "Escape") return setMode("view");
        const n = parseInt(e.key, 10);
        if (n >= 1 && n <= REASON_CODES.length) {
          e.preventDefault();
          void decide({ decision: "REJECT", reason_code: REASON_CODES[n - 1] });
        }
        return;
      }

      if (mode === "promote") {
        if (e.key === "Escape") return setMode("view");
        const secs = item?.secondaries ?? [];
        const n = parseInt(e.key, 10);
        if (n >= 1 && n <= secs.length) {
          e.preventDefault();
          void decide({
            decision: "PROMOTE",
            edit: { promote_mapping_id: secs[n - 1].id },
          });
        }
        return;
      }

      if (mode === "edit") {
        if (e.key === "Escape") return setMode("view");
        if (e.key === "j" || e.key === "ArrowDown") {
          e.preventDefault();
          setSel((s) => Math.min(s + 1, cands.length - 1));
        } else if (e.key === "k" || e.key === "ArrowUp") {
          e.preventDefault();
          setSel((s) => Math.max(s - 1, 0));
        } else if (e.key === "Enter" && cands[sel]) {
          e.preventDefault();
          void decide(
            { decision: "EDIT", edit: { topic_id: cands[sel].topic_id } },
            "mapping edited — press a to approve",
          );
        }
        return;
      }

      // view mode
      if (isKnowledge) {
        switch (e.key) {
          case "j":
          case "ArrowDown":
            e.preventDefault();
            setKsSel((s) => Math.min(s + 1, kItems.length - 1));
            break;
          case "k":
          case "ArrowUp":
            e.preventDefault();
            setKsSel((s) => Math.max(s - 1, 0));
            break;
          case "x":
            e.preventDefault();
            void toggleReject();
            break;
          case "a":
            e.preventDefault();
            void decide({ decision: "APPROVE" }, "spec approved");
            break;
          case "E":
            e.preventDefault();
            void approveAndExport();
            break;
          case "r":
            e.preventDefault();
            setMode("reject");
            break;
          case "s":
            e.preventDefault();
            void skip();
            break;
        }
        return;
      }

      switch (e.key) {
        case "a":
          e.preventDefault();
          void decide({ decision: "APPROVE" });
          break;
        case "p": {
          e.preventDefault();
          const secs = item?.secondaries ?? [];
          if (secs.length === 0) break;
          if (secs.length === 1) {
            void decide({
              decision: "PROMOTE",
              edit: { promote_mapping_id: secs[0].id },
            });
          } else {
            setMode("promote");
          }
          break;
        }
        case "r":
          e.preventDefault();
          setMode("reject");
          break;
        case "e":
          e.preventDefault();
          setSel(
            Math.max(
              0,
              cands.findIndex((c) => c.topic_id === item?.mapping?.topic_id),
            ),
          );
          setMode("edit");
          break;
        case "s":
          e.preventDefault();
          void skip();
          break;
        case "b":
          e.preventDefault();
          void batch();
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    mode,
    sel,
    ksSel,
    item,
    isKnowledge,
    kItems.length,
    decide,
    skip,
    batch,
    toggleReject,
    approveAndExport,
  ]);

  if (!ready) return <p className="muted">loading…</p>;

  return (
    <div>
      <Stats s={stats} />

      {!item ? (
        <div className="card">
          <h2>Queue empty</h2>
          <p className="muted">
            No open review items
            {skipped.length ? " (some were skipped this session)" : ""}.
            {skipped.length > 0 && (
              <>
                {" "}
                <button
                  onClick={() => {
                    setSkipped([]);
                    void refresh([]);
                  }}
                >
                  clear skips
                </button>
              </>
            )}
          </p>
        </div>
      ) : isKnowledge ? (
        <div className="card">
          <KnowledgeCard item={item} sel={ksSel} />
          {mode === "reject" && (
            <div style={{ marginTop: 12 }}>
              <p>
                <b>Reject the whole spec — pick a reason:</b>{" "}
                <span className="muted">(Esc to cancel)</span>
              </p>
              <ul style={{ listStyle: "none", padding: 0 }}>
                {REASON_CODES.map((rc, i) => (
                  <li key={rc} style={{ margin: "4px 0" }}>
                    <span className="kbd">{i + 1}</span> {rc}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {msg && (
            <p className="muted" style={{ marginTop: 10 }}>
              {msg}
            </p>
          )}
          {err && <p className="err">{err}</p>}
        </div>
      ) : (
        <div className="card">
          <div className="row">
            <span className="pill">{item.item_type}</span>
            {item.audit_sample ? (
              <span
                className="pill good"
                title="a confident mapping queued for a spot-check, not because it is risky"
              >
                audit spot-check
              </span>
            ) : (
              <span className="pill warn">risk {item.risk.toFixed(2)}</span>
            )}
            {item.confidence != null && (
              <span className="pill">
                mapping confidence {item.confidence.toFixed(2)}
              </span>
            )}
            <span className="muted mono">#{item.id}</span>
          </div>

          <h2 style={{ marginBottom: 4 }}>{item.chunk_heading ?? item.title}</h2>

          {item.chunk_stem && (
            <div
              className="chunk"
              style={{ borderLeft: "3px solid var(--accent)" }}
            >
              <span className="muted">shared stem (parent task): </span>
              {item.chunk_stem}
            </div>
          )}
          {item.chunk_text && <div className="chunk">{item.chunk_text}</div>}

          {item.mapping && (
            <p>
              suggested topic:{" "}
              <b className="mono">{item.mapping.topic_code ?? "— unmapped —"}</b>{" "}
              <span className="muted">
                ({item.mapping.content_type}
                {item.mapping.difficulty != null
                  ? `, difficulty ${item.mapping.difficulty}`
                  : ""}
                {item.mapping.model ? `, ${item.mapping.model}` : ", stub"})
              </span>
              {item.mapping.rationale && (
                <>
                  <br />
                  <span className="muted">{item.mapping.rationale}</span>
                </>
              )}
            </p>
          )}

          {item.secondaries.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div className="muted" style={{ marginBottom: 4 }}>
                also plausibly tests
                {item.secondaries.length === 1 ? (
                  <>
                    {" "}
                    (<span className="kbd">p</span> promotes it to primary)
                  </>
                ) : (
                  <>
                    {" "}
                    (<span className="kbd">p</span> then 1–
                    {item.secondaries.length} promotes)
                  </>
                )}
                :
              </div>
              {item.secondaries.map((s, i) => (
                <div
                  key={s.id}
                  className="chunk"
                  style={{ margin: "4px 0", padding: "8px 12px" }}
                >
                  <span className="kbd">{i + 1}</span>{" "}
                  <b className="mono">{s.topic_code ?? "—"}</b>{" "}
                  <span className="muted">
                    conf {s.confidence.toFixed(2)}
                    {s.topic_name ? ` · ${s.topic_name}` : ""}
                  </span>
                  {s.rationale && (
                    <>
                      <br />
                      <span className="muted">{s.rationale}</span>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {mode === "promote" && (
            <div style={{ marginTop: 12 }}>
              <p>
                <b>Promote which secondary to primary?</b>{" "}
                <span className="muted">(press its number, Esc to cancel)</span>
              </p>
            </div>
          )}

          {mode === "reject" && (
            <div style={{ marginTop: 12 }}>
              <p>
                <b>Reject — pick a reason:</b>{" "}
                <span className="muted">(Esc to cancel)</span>
              </p>
              <ul style={{ listStyle: "none", padding: 0 }}>
                {REASON_CODES.map((rc, i) => (
                  <li key={rc} style={{ margin: "4px 0" }}>
                    <span className="kbd">{i + 1}</span> {rc}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {mode === "edit" && (
            <div style={{ marginTop: 12 }}>
              <p>
                <b>Edit topic</b>{" "}
                <span className="muted">
                  (<span className="kbd">j</span>/<span className="kbd">k</span>{" "}
                  move, <span className="kbd">Enter</span> apply, Esc cancel)
                </span>
              </p>
              <div style={{ maxHeight: 260, overflowY: "auto" }}>
                {item.candidates.map((c, i) => (
                  <div
                    key={c.topic_id}
                    className={"candidate" + (i === sel ? " sel" : "")}
                  >
                    <span className="mono">{c.code}</span> — {c.name}
                  </div>
                ))}
              </div>
            </div>
          )}

          {msg && (
            <p className="muted" style={{ marginTop: 10 }}>
              {msg}
            </p>
          )}
          {err && <p className="err">{err}</p>}
        </div>
      )}

      <div className="hint">
        {mode === "view" && isKnowledge && (
          <>
            <span className="kbd">a</span> approve spec &nbsp;
            <span className="kbd">E</span> approve &amp; export &nbsp;
            <span className="kbd">x</span> reject/restore selected item &nbsp;
            <span className="kbd">j</span>/<span className="kbd">k</span> move
            &nbsp;
            <span className="kbd">r</span> reject spec &nbsp;
            <span className="kbd">s</span> skip &nbsp; &nbsp;·&nbsp; reviewer:{" "}
            <span className="mono">{reviewer.current}</span>
          </>
        )}
        {mode === "view" && !isKnowledge && (
          <>
            <span className="kbd">a</span> approve &nbsp;
            <span className="kbd">p</span> promote secondary &nbsp;
            <span className="kbd">r</span> reject &nbsp;
            <span className="kbd">e</span> edit topic &nbsp;
            <span className="kbd">s</span> skip &nbsp;
            <span className="kbd">b</span> batch-approve group &nbsp; &nbsp;·&nbsp;
            reviewer: <span className="mono">{reviewer.current}</span>
          </>
        )}
        {mode === "reject" && (
          <>press 1–{REASON_CODES.length} for a reason, Esc to cancel</>
        )}
        {mode === "edit" && (
          <>j/k to move, Enter to apply the topic, Esc to cancel</>
        )}
        {mode === "promote" && (
          <>press the secondary&rsquo;s number, Esc to cancel</>
        )}
      </div>
    </div>
  );
}
