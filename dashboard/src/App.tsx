import { useCallback, useEffect, useState } from "react";
import type { ApplicationStatus, HostInfo, StatusApiResponse } from "./types";
import { formatBytes } from "./format";

const SETUP_HINT = "Run setup_ai.sh from a terminal";

async function resolveToken(): Promise<string> {
  if (window.__DASHBOARD_TOKEN__) {
    return window.__DASHBOARD_TOKEN__;
  }
  const res = await fetch("/api/bootstrap");
  if (!res.ok) {
    throw new Error("Could not load dashboard token (is the API server running?)");
  }
  const body = (await res.json()) as { token?: string };
  if (!body.token) {
    throw new Error("Invalid bootstrap response");
  }
  window.__DASHBOARD_TOKEN__ = body.token;
  return body.token;
}

function AppStatusTable({ apps }: { apps: ApplicationStatus[] }) {
  const sorted = [...apps].sort((a, b) => a.id.localeCompare(b.id));

  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            <th>Application</th>
            <th>Installed</th>
            <th>Version</th>
            <th>Action</th>
            <th>Detail</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {sorted.map((app) => (
            <tr key={app.id}>
              <td>{app.id}</td>
              <td>
                <span className={`badge ${app.installed ? "ok" : "no"}`}>
                  {app.installed ? "yes" : "no"}
                </span>
              </td>
              <td>{app.version || "—"}</td>
              <td>{app.action}</td>
              <td>{app.detail}</td>
              <td>
                <button type="button" disabled title={SETUP_HINT}>
                  Manage
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HostSection({ host }: { host: HostInfo }) {
  return (
    <dl className="host-grid">
      <div>
        <dt>OS</dt>
        <dd>{host.os}{host.distro ? ` (${host.distro})` : ""}</dd>
      </div>
      <div>
        <dt>Architecture</dt>
        <dd>{host.arch}</dd>
      </div>
      <div>
        <dt>Memory</dt>
        <dd>{formatBytes(host.memory_bytes)}</dd>
      </div>
      <div>
        <dt>Disk free</dt>
        <dd>{formatBytes(host.disk_free_bytes)}</dd>
      </div>
      <div>
        <dt>Home</dt>
        <dd>{host.home}</dd>
      </div>
      <div>
        <dt>Package managers</dt>
        <dd>
          {[
            host.brew ? "Homebrew" : null,
            host.winget ? "winget" : null,
          ]
            .filter(Boolean)
            .join(", ") || "—"}
        </dd>
      </div>
    </dl>
  );
}

function LocalInferenceSection({ apps }: { apps: ApplicationStatus[] }) {
  const ollama = apps.find((a) => a.id === "ollama");
  const lmStudio = apps.find((a) => a.id === "lm-studio");

  const hasReachabilityFields =
    ollama &&
    lmStudio &&
    ("reachable" in ollama || "running" in ollama || "reachable" in lmStudio);

  if (!hasReachabilityFields) {
    return (
      <p className="note">
        Local inference reachability is not included in the current status JSON.
        Ollama and LM Studio install state appears in the applications table above
        when reported by <code>python3 -m ai status --json</code>.
      </p>
    );
  }

  return (
    <ul className="note" style={{ margin: 0, paddingLeft: "1.2rem" }}>
      <li>
        Ollama:{" "}
        {(ollama as ApplicationStatus & { reachable?: boolean }).reachable
          ? "reachable"
          : "not reachable"}
      </li>
      <li>
        LM Studio:{" "}
        {(lmStudio as ApplicationStatus & { reachable?: boolean }).reachable
          ? "reachable"
          : "not reachable"}
      </li>
    </ul>
  );
}

export default function App() {
  const [loading, setLoading] = useState(true);
  const [response, setResponse] = useState<StatusApiResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const token = await resolveToken();
      const res = await fetch("/api/status", {
        headers: { "X-Dashboard-Token": token },
      });
      const body = (await res.json()) as StatusApiResponse & { error?: string };
      if (!res.ok) {
        setFetchError(body.error ?? `HTTP ${res.status}`);
        setResponse(null);
      } else {
        setResponse(body);
      }
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : String(err));
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const apps = response?.status?.applications ?? [];
  const host = response?.status?.host;

  return (
    <>
      <h1>AI Workstation Dashboard</h1>
      <p className="subtitle">
        Local management view for this machine. Bind: 127.0.0.1 only.
      </p>

      <div className="toolbar">
        <button type="button" className="secondary" onClick={() => void load()} disabled={loading}>
          Refresh status
        </button>
        {loading && <span className="spinner">Loading…</span>}
      </div>

      {fetchError && <div className="error-box">{fetchError}</div>}

      {response?.error && (
        <section>
          <h2>Status command error</h2>
          <div className="error-box">{response.error}</div>
        </section>
      )}

      <section>
        <h2>Application status</h2>
        {response?.status?.applications ? (
          <AppStatusTable apps={response.status.applications} />
        ) : (
          <p className="note">
            {loading
              ? "Waiting for status…"
              : "No application data. Ensure the repo Python package is available."}
          </p>
        )}
      </section>

      <section>
        <h2>Host</h2>
        {host ? (
          <HostSection host={host} />
        ) : (
          <p className="note">Host metrics unavailable until status succeeds.</p>
        )}
      </section>

      <section>
        <h2>Providers</h2>
        <p className="note">
          API keys and cloud provider configuration are managed by{" "}
          <code>ai/providers</code>. This dashboard does not display or store secrets.
        </p>
        <button type="button" disabled title={SETUP_HINT} style={{ marginTop: "0.5rem" }}>
          Configure providers
        </button>
      </section>

      <section>
        <h2>Local inference</h2>
        {apps.length > 0 ? (
          <LocalInferenceSection apps={apps} />
        ) : (
          <p className="note">No inference data yet.</p>
        )}
      </section>
    </>
  );
}
