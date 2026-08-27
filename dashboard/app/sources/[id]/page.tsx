import { api } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function SourceDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const id = Number(params.id);
  let chunks;
  try {
    chunks = await api.sourceChunks(id);
  } catch (e) {
    return (
      <div className="card">
        <p className="err">Could not load source {id}: {String(e)}</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Source #{id} — chunks</h2>
      <p className="muted">
        {chunks.length} chunks. Deterministic extraction has no confidence
        (shown as “—”); a mapping status of AI_SUGGESTED means it never entered
        the review queue.
      </p>
      {chunks.map((c) => (
        <div className="card" key={c.id} style={{ marginBottom: 12 }}>
          <div className="row">
            <b>{c.heading ?? `chunk ${c.order_index}`}</b>
            <span className="pill">{c.content_type}</span>
            <span className="muted">
              extraction confidence: {c.confidence ?? "—"}
            </span>
            {c.mapping && (
              <span
                className={
                  "pill " +
                  (c.mapping.mapping_status === "APPROVED"
                    ? "good"
                    : c.mapping.mapping_status === "REJECTED"
                      ? "bad"
                      : c.mapping.mapping_status === "REVIEW_REQUIRED"
                        ? "warn"
                        : "")
                }
              >
                {c.mapping.mapping_status}
                {c.mapping.topic_code ? ` → ${c.mapping.topic_code}` : ""}{" "}
                ({c.mapping.confidence.toFixed(2)})
              </span>
            )}
          </div>
          <div className="chunk" style={{ marginBottom: 0 }}>
            {c.text}
          </div>
        </div>
      ))}
    </div>
  );
}
