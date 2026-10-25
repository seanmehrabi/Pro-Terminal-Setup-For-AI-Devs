import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from "node:http";
import { spawn } from "node:child_process";
import {
  createReadStream,
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
  chmodSync,
} from "node:fs";
import { randomBytes } from "node:crypto";
import { dirname, join, extname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DASHBOARD_ROOT = join(__dirname, "..");
const REPO_ROOT = join(DASHBOARD_ROOT, "..");
const DIST_DIR = join(DASHBOARD_ROOT, "dist");
const RUN_DIR = join(DASHBOARD_ROOT, ".run");
const TOKEN_PATH = join(RUN_DIR, "token");
const LEGACY_TOKEN_PATH = join(DASHBOARD_ROOT, ".token");

const HOST = "127.0.0.1";
const PORT = Number(process.env.DASHBOARD_PORT ?? 3847);
const STATUS_TIMEOUT_MS = 20_000;

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".json": "application/json",
  ".woff2": "font/woff2",
};

function ensureToken(): string {
  const paths = [TOKEN_PATH, LEGACY_TOKEN_PATH];
  for (const p of paths) {
    if (existsSync(p)) {
      return readFileSync(p, "utf8").trim();
    }
  }

  if (!existsSync(RUN_DIR)) {
    mkdirSync(RUN_DIR, { mode: 0o700 });
  }

  const token = randomBytes(32).toString("hex");
  writeFileSync(TOKEN_PATH, token + "\n", { mode: 0o600 });
  try {
    chmodSync(TOKEN_PATH, 0o600);
  } catch {
    /* best effort on platforms that support it */
  }
  return token;
}

let dashboardToken = ensureToken();

function isLoopback(req: IncomingMessage): boolean {
  const remote = req.socket.remoteAddress ?? "";
  const loopback =
    remote === "127.0.0.1" ||
    remote === "::1" ||
    remote === "::ffff:127.0.0.1" ||
    remote.endsWith("127.0.0.1");

  const hostHeader = (req.headers.host ?? "").split(":")[0]?.toLowerCase();
  const hostOk =
    !hostHeader ||
    hostHeader === "localhost" ||
    hostHeader === "127.0.0.1" ||
    hostHeader === "[::1]";

  return loopback && hostOk;
}

function readToken(req: IncomingMessage, url: URL): string | null {
  const header = req.headers["x-dashboard-token"];
  if (typeof header === "string" && header.length > 0) {
    return header;
  }
  const query = url.searchParams.get("token");
  if (query) {
    return query;
  }
  return null;
}

function tokenValid(provided: string | null): boolean {
  if (!provided) {
    return false;
  }
  const a = Buffer.from(provided);
  const b = Buffer.from(dashboardToken);
  if (a.length !== b.length) {
    return false;
  }
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a[i]! ^ b[i]!;
  }
  return diff === 0;
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(payload);
}

function runStatusJson(): Promise<{ ok: true; data: unknown } | { ok: false; error: string }> {
  return new Promise((resolve) => {
    const child = spawn("python3", ["-m", "ai", "status", "--json"], {
      cwd: REPO_ROOT,
      stdio: ["ignore", "pipe", "pipe"],
      env: process.env,
    });

    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      resolve({ ok: false, error: `Timed out after ${STATUS_TIMEOUT_MS / 1000}s` });
    }, STATUS_TIMEOUT_MS);

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ ok: false, error: err.message });
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        const msg = stderr.trim() || stdout.trim() || `python exited with code ${code}`;
        resolve({ ok: false, error: msg });
        return;
      }
      try {
        const data = JSON.parse(stdout) as unknown;
        resolve({ ok: true, data });
      } catch {
        resolve({ ok: false, error: "Invalid JSON from python3 -m ai status --json" });
      }
    });
  });
}

function injectToken(html: string, token: string): string {
  const script = `<script>window.__DASHBOARD_TOKEN__=${JSON.stringify(token)};</script>`;
  if (html.includes("</head>")) {
    return html.replace("</head>", `${script}</head>`);
  }
  return script + html;
}

function serveStatic(pathname: string, res: ServerResponse, token: string): void {
  let rel = pathname === "/" ? "/index.html" : pathname;
  const filePath = join(DIST_DIR, rel);

  if (!filePath.startsWith(DIST_DIR)) {
    sendJson(res, 403, { error: "Forbidden" });
    return;
  }

  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    const indexPath = join(DIST_DIR, "index.html");
    if (!existsSync(indexPath)) {
      sendJson(res, 503, {
        error: "UI not built. Run npm run build in dashboard/, or use npm run dev for development.",
      });
      return;
    }
    let html = readFileSync(indexPath, "utf8");
    html = injectToken(html, token);
    res.writeHead(200, {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    });
    res.end(html);
    return;
  }

  if (rel.endsWith(".html") || rel === "/index.html") {
    let html = readFileSync(filePath, "utf8");
    html = injectToken(html, token);
    res.writeHead(200, {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    });
    res.end(html);
    return;
  }

  const ext = extname(filePath);
  res.writeHead(200, {
    "Content-Type": MIME[ext] ?? "application/octet-stream",
    "Cache-Control": ext === ".html" ? "no-store" : "public, max-age=3600",
  });
  createReadStream(filePath).pipe(res);
}

async function handleRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
  if (!isLoopback(req)) {
    sendJson(res, 403, { error: "Forbidden: loopback only" });
    return;
  }

  const url = new URL(req.url ?? "/", `http://${HOST}:${PORT}`);
  const method = req.method ?? "GET";

  if (method === "GET" && url.pathname === "/api/bootstrap") {
    sendJson(res, 200, { token: dashboardToken });
    return;
  }

  if (method === "GET" && url.pathname === "/api/status") {
    const provided = readToken(req, url);
    const authOk = tokenValid(provided);
    if (!authOk) {
      sendJson(res, 401, {
        auth: { ok: false },
        error: "Missing or invalid X-Dashboard-Token",
      });
      return;
    }

    const result = await runStatusJson();
    if (result.ok) {
      sendJson(res, 200, {
        auth: { ok: true },
        status: result.data,
        error: null,
      });
    } else {
      sendJson(res, 200, {
        auth: { ok: true },
        status: null,
        error: result.error,
      });
    }
    return;
  }

  if (method === "GET" && !url.pathname.startsWith("/api")) {
    serveStatic(url.pathname, res, dashboardToken);
    return;
  }

  sendJson(res, 404, { error: "Not found" });
}

const server = createServer((req, res) => {
  void handleRequest(req, res);
});

server.listen(PORT, HOST, () => {
  console.log(`Dashboard listening on http://${HOST}:${PORT}`);
});
