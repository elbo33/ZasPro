import Link from "next/link";
import { api } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  let docs;
  try {
    docs = await api.sources();
  } catch (e) {
    return (
      <div className="card">
        <h2>Sources</h2>
        <p className="err">Could not reach the API: {String(e)}</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Source documents</h2>
      <table>
        <thead>
          <tr>
            <th>file</th>
            <th>session</th>
            <th>status</th>
            <th>chunks</th>
            <th>exercises</th>
            <th>figures</th>
            <th>mappings</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((d) => (
            <tr key={d.id}>
              <td>
                <Link href={`/sources/${d.id}`} className="mono">
                  {d.file_ref}
                </Link>
              </td>
              <td>
                {d.session_code ?? "—"}
                {d.paper_version ? ` ${d.paper_version}` : ""}
              </td>
              <td>{d.extraction_status}</td>
              <td>{d.chunks}</td>
              <td>{d.exercises}</td>
              <td>{d.figures}</td>
              <td className="muted">
                {Object.entries(d.mappings_by_status)
                  .filter(([, n]) => n > 0)
                  .map(([k, n]) => `${k} ${n}`)
                  .join(", ") || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {docs.length === 0 && <p className="muted">Nothing ingested yet.</p>}
    </div>
  );
}
