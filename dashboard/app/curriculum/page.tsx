import { api } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function CurriculumPage() {
  let units;
  try {
    units = await api.curriculum();
  } catch (e) {
    return (
      <div className="card">
        <h2>Curriculum</h2>
        <p className="err">Could not reach the API: {String(e)}</p>
        <p className="muted">Start it with <span className="mono">uv run uvicorn zaspro.api.app:app</span>.</p>
      </div>
    );
  }

  const topicCount = units.reduce((n, u) => n + u.topics.length, 0);
  const withContent = units.reduce(
    (n, u) => n + u.topics.filter((t) => t.mapped_chunks > 0).length,
    0,
  );

  return (
    <div>
      <div className="statbar">
        <div className="stat">
          <b>{units.length}</b>
          <span>units</span>
        </div>
        <div className="stat">
          <b>{topicCount}</b>
          <span>podstawowy requirements</span>
        </div>
        <div className="stat">
          <b>{withContent}</b>
          <span>with mapped content</span>
        </div>
        <div className="stat">
          <b>{topicCount - withContent}</b>
          <span>still empty</span>
        </div>
      </div>

      {units.map((u) => (
        <div className="card" key={u.id} style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>
            <span className="mono">{u.code}</span> — {u.name}
          </h3>
          <table>
            <thead>
              <tr>
                <th>code</th>
                <th>requirement</th>
                <th title="chunks whose primary requirement is this topic">primary</th>
                <th title="chunks that name this topic only as a secondary">also tests</th>
                <th>approved</th>
                <th>exercises</th>
              </tr>
            </thead>
            <tbody>
              {u.topics.map((t) => (
                <tr key={t.id}>
                  <td className="mono">{t.code}</td>
                  <td>{t.name}</td>
                  <td>{t.mapped_chunks || <span className="muted">0</span>}</td>
                  <td>{t.also_tests || <span className="muted">0</span>}</td>
                  <td>{t.approved_chunks || <span className="muted">0</span>}</td>
                  <td>{t.exercises || <span className="muted">0</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
