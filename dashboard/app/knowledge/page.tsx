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
      setBusy(r.section_id);
      setErr(null);
      setMsg(null);
      try {
        let reviewer = "reviewer";
        try {
          reviewer = window.localStorage.getItem("zaspro.reviewer") || "reviewer";
        } catch {
          /* ignore */
        }
        const res = await api.exportKnowledge(r.section_id, reviewer);
        setMsg(res.ok ? `${r.slug} -> ${res.path}` : `${r.slug}: ${res.error}`);
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

  const written = rows.filter((r) => r.review_status);
  const approved = rows.filter((r) => r.review_status === "APPROVED");
  const exported = rows.filter((r) => r.exported_at);

  return (
    <div>
      <h2>Knowledge layer</h2>
      <p className="muted">
        One row per teaching section. Review each spec on the{" "}
        <a href="/">review queue</a> (one KNOWLEDGE_SPEC card per section), then
        export the approved ones to{" "}
        <span className="mono">knowledge/sections/</span> — the committed file is
        the freeze (ADR 0012).
      </p>

      <div className="statbar">
        <div className="stat">
          <b>{rows.length}</b>
          <span>sections</span>
        </div>
        <div className="stat">
          <b>{written.length}</b>
          <span>written</span>
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
              <th>#</th>
              <th>section</th>
              <th>requirements</th>
              {KINDS.map((k) => (
                <th key={k}>{k.slice(0, 4)}</th>
              ))}
              <th>review</th>
              <th>export</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.section_id}>
                <td className="muted">{r.order_index}</td>
                <td>
                  {r.name.length > 64 ? r.name.slice(0, 62) + "…" : r.name}
                  <br />
                  <span className="muted mono">{r.slug}</span>
                </td>
                <td className="mono">{r.requirement_codes.join(", ")}</td>
                {KINDS.map((k) => (
                  <td key={k} className={r.counts[k] ? "" : "muted"}>
                    {r.counts[k] ?? 0}
                  </td>
                ))}
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
                    <span className="muted">not written</span>
                  )}
                </td>
                <td>
                  {r.exported_at ? (
                    <span className="pill good">frozen</span>
                  ) : r.review_status === "APPROVED" ? (
                    <button
                      disabled={busy === r.section_id}
                      onClick={() => doExport(r)}
                    >
                      {busy === r.section_id ? "…" : "export"}
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
