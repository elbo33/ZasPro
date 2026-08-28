"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type KnowledgeIndexRow } from "../lib/api";

const KINDS = ["concept", "formula", "method", "example", "objective", "misconception"];

export default function KnowledgePage() {
  const [rows, setRows] = useState<KnowledgeIndexRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setRows(await api.knowledgeIndex());
    } catch (e) {
      setErr(String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const doExport = useCallback(
    async (r: KnowledgeIndexRow) => {
      setBusy(r.topic_id);
      setErr(null);
      setMsg(null);
      try {
        let reviewer = "reviewer";
        try {
          reviewer = window.localStorage.getItem("zaspro.reviewer") || "reviewer";
        } catch {
          /* ignore */
        }
        const res = await api.exportKnowledge(r.topic_id, reviewer);
        setMsg(res.ok ? `${r.code} -> ${res.path}` : `${r.code}: ${res.error}`);
        await load();
      } catch (e) {
        setErr(String(e));
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  if (err)
    return (
      <div className="card">
        <h2>Knowledge</h2>
        <p className="err">Could not reach the API: {err}</p>
      </div>
    );
  if (!rows) return <p className="muted">loading…</p>;

  const extracted = rows.filter((r) => r.review_status);
  const approved = rows.filter((r) => r.review_status === "APPROVED");
  const exported = rows.filter((r) => r.exported_at);

  return (
    <div>
      <h2>Knowledge layer</h2>
      <p className="muted">
        One row per podstawowy requirement. Review each spec on the{" "}
        <a href="/">review queue</a> (one KNOWLEDGE_SPEC card per topic), then
        export the approved ones to <span className="mono">knowledge/topics/</span>{" "}
        — the committed file is the freeze (ADR 0011).
      </p>

      <div className="statbar">
        <div className="stat">
          <b>{rows.length}</b>
          <span>requirements</span>
        </div>
        <div className="stat">
          <b>{extracted.length}</b>
          <span>extracted</span>
        </div>
        <div className="stat">
          <b>{approved.length}</b>
          <span>approved</span>
        </div>
        <div className="stat">
          <b>{exported.length}</b>
          <span>exported (frozen)</span>
        </div>
      </div>

      {msg && <p className="muted">{msg}</p>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>code</th>
              <th>requirement</th>
              <th>ex</th>
              {KINDS.map((k) => (
                <th key={k}>{k.slice(0, 4)}</th>
              ))}
              <th>agent-only</th>
              <th>review</th>
              <th>export</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.topic_id}>
                <td className="mono">{r.code}</td>
                <td>
                  {r.name.length > 60 ? r.name.slice(0, 58) + "…" : r.name}
                  <br />
                  <span className="muted">{r.unit}</span>
                </td>
                <td>{r.exercises}</td>
                {KINDS.map((k) => (
                  <td key={k} className={r.counts[k] ? "" : "muted"}>
                    {r.counts[k] ?? 0}
                  </td>
                ))}
                <td
                  className={r.agent_knowledge_items ? "" : "muted"}
                  title="items with AGENT_KNOWLEDGE provenance"
                >
                  {r.agent_knowledge_items}
                </td>
                <td>
                  {r.review_status ? (
                    <span
                      className={
                        "pill" +
                        (r.review_status === "APPROVED"
                          ? " good"
                          : r.review_status === "REJECTED"
                            ? " bad"
                            : " warn")
                      }
                    >
                      {r.review_status}
                    </span>
                  ) : (
                    <span className="muted">not extracted</span>
                  )}
                </td>
                <td>
                  {r.exported_at ? (
                    <span className="pill good">frozen</span>
                  ) : r.review_status === "APPROVED" ? (
                    <button
                      disabled={busy === r.topic_id}
                      onClick={() => doExport(r)}
                    >
                      {busy === r.topic_id ? "…" : "export"}
                    </button>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
