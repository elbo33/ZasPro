import { api } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function CalibrationPage() {
  let cal;
  try {
    cal = await api.calibration();
  } catch (e) {
    return (
      <div className="card">
        <h2>Mapping calibration</h2>
        <p className="err">Could not reach the API: {String(e)}</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Mapping agent — agreement vs confidence</h2>
      <p className="muted">
        How often a mapping was accepted <b>unchanged</b>, by the agent&rsquo;s own
        confidence band. Set <span className="mono">AUTO_APPROVE_THRESHOLD</span>{" "}
        from where agreement actually holds, not from a guess (ADR 0009). Run a
        calibration pass with{" "}
        <span className="mono">
          zaspro.mapping.run &lt;arkusz&gt; --review-all
        </span>{" "}
        then work the whole queue.
      </p>

      <div className="statbar">
        <div className="stat">
          <b>{cal.resolved}</b>
          <span>resolved</span>
        </div>
        <div className="stat">
          <b>{cal.pending}</b>
          <span>still open</span>
        </div>
        <div className="stat">
          <b>{(cal.target * 100).toFixed(0)}%</b>
          <span>target agreement</span>
        </div>
        <div className="stat">
          <b>
            {cal.recommended_threshold != null
              ? cal.recommended_threshold.toFixed(2)
              : "—"}
          </b>
          <span>evidence-based threshold</span>
        </div>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>confidence band</th>
              <th>n</th>
              <th>accepted unchanged</th>
              <th>changed / rejected</th>
              <th>agreement</th>
              <th>audit-sampled</th>
            </tr>
          </thead>
          <tbody>
            {cal.bands.map((b) => (
              <tr key={b.lo}>
                <td className="mono">
                  [{b.lo.toFixed(1)}, {b.hi.toFixed(1)}
                  {b.hi < 1 ? ")" : "]"}
                </td>
                <td>{b.n}</td>
                <td>{b.agree}</td>
                <td>{b.disagree}</td>
                <td>
                  {b.agreement != null
                    ? `${(b.agreement * 100).toFixed(0)}%`
                    : "—"}
                </td>
                <td className="muted">{b.audit}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {cal.notes.length > 0 && (
          <ul className="muted">
            {cal.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
