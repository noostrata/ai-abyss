"""Admin dashboard API endpoints for telemetry and monitoring."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.telemetry.db import TelemetryDB

router = APIRouter(prefix="/admin")

_db: TelemetryDB | None = None
_api_key: str = ""


def set_db(db: TelemetryDB) -> None:
    global _db
    _db = db


def set_api_key(key: str) -> None:
    global _api_key
    _api_key = key


def _get_db() -> TelemetryDB:
    if _db is None:
        raise RuntimeError("Dashboard DB not initialized")
    return _db


async def verify_api_key(request: Request) -> None:
    """Dependency that checks the API key on admin endpoints."""
    if not _api_key:
        return  # No key configured — allow access
    key = request.headers.get("x-api-key", "") or request.query_params.get("api_key", "")
    if key != _api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


def _build_dashboard_html() -> str:
    """Build the self-contained HTML dashboard page with login gate."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Abyss — Dashboard</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  background:#000;color:#777;
  font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,"Courier New",monospace;
  font-size:13px;line-height:1.6;
}
a{color:#c00;text-decoration:none}
a:hover{text-decoration:underline}
h1{font-size:18px;font-weight:400;color:#c00;letter-spacing:.08em;text-transform:uppercase}

/* Login */
.login-wrap{display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{background:#000;border:1px solid #222;padding:40px 36px;width:320px;text-align:center}
.login-box h1{margin-bottom:4px}
.login-box .sub{color:#444;font-size:12px;margin-bottom:28px;letter-spacing:.04em}
.login-box input{
  width:100%;padding:9px 10px;background:#000;border:1px solid #333;
  color:#aaa;font-size:13px;font-family:inherit;margin-bottom:12px;outline:none;
}
.login-box input:focus{border-color:#c00}
.login-box button{
  width:100%;padding:9px;background:#c00;border:none;
  color:#000;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;letter-spacing:.04em;text-transform:uppercase;
}
.login-box button:hover{background:#e00}
.login-error{color:#c00;font-size:12px;margin-top:8px;display:none}

/* Dashboard */
.dashboard{display:none;padding:20px 24px;max-width:1200px;margin:0 auto}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;padding-bottom:14px;border-bottom:1px solid #1a1a1a}
.header-right{font-size:12px;color:#555;display:flex;align-items:center;gap:12px}
.logout-btn{background:none;border:1px solid #333;padding:2px 10px;color:#555;font-size:11px;cursor:pointer;font-family:inherit;text-transform:uppercase;letter-spacing:.04em}
.logout-btn:hover{color:#c00;border-color:#c00}
.refresh-indicator{display:inline-block;width:6px;height:6px;background:#0a0;margin-right:6px;vertical-align:middle}
.refresh-indicator.fetching{background:#a80}

/* Cards */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:28px}
.card{background:#000;border:1px solid #1a1a1a;padding:14px 16px}
.card-label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:4px}
.card-value{font-size:26px;font-weight:700;color:#aaa}
.card-value.hostile{color:#c00}
.card-value.compliant{color:#a80}
.card-value.human{color:#0a0}
.card-value.callback{color:#c00}

/* Tables */
.section{margin-bottom:28px}
.section-title{font-size:12px;font-weight:400;color:#888;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #1a1a1a;text-transform:uppercase;letter-spacing:.08em}
table{width:100%;border-collapse:collapse;background:#000;border:1px solid #1a1a1a}
thead th{background:#0a0a0a;text-align:left;padding:8px 10px;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#555;font-weight:400;border-bottom:1px solid #1a1a1a}
tbody td{padding:7px 10px;border-bottom:1px solid #111;font-size:12px;color:#777;vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:#0a0a0a}
.rate-green{color:#0a0;font-weight:700}
.rate-zero{color:#333}
.violation{color:#c00}
.ok{color:#555}
.mono{font-family:inherit;font-size:11px}
.truncated{max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* Expandable headers */
.expand-btn{
  background:#111;color:#555;border:1px solid #222;padding:1px 8px;
  font-size:10px;cursor:pointer;font-family:inherit;text-transform:uppercase;letter-spacing:.04em;
}
.expand-btn:hover{background:#1a1a1a;color:#aaa}
.headers-detail{display:none;margin-top:6px;padding:8px;background:#000;border:1px solid #1a1a1a;font-size:11px;white-space:pre-wrap;word-break:break-all;max-height:200px;overflow-y:auto;color:#555}
.headers-detail.open{display:block}

.empty-state{padding:20px;text-align:center;color:#333;font-style:normal;letter-spacing:.04em}
.error-banner{background:#1a0000;border:1px solid #c00;color:#c00;padding:8px 12px;margin-bottom:16px;display:none}
</style>
</head>
<body>

<!-- Login Screen -->
<div class="login-wrap" id="loginScreen">
  <div class="login-box">
    <h1>AI Abyss</h1>
    <div class="sub">Dashboard</div>
    <form id="loginForm">
      <input type="password" id="apiKeyInput" placeholder="API Key" autocomplete="off" autofocus>
      <button type="submit">Authenticate</button>
    </form>
    <div class="login-error" id="loginError">Invalid API key</div>
  </div>
</div>

<!-- Dashboard (hidden until auth) -->
<div class="dashboard" id="dashboardScreen">
<div class="header">
  <h1>AI Abyss &mdash; Dashboard</h1>
  <div class="header-right">
    <span class="refresh-indicator" id="refreshDot"></span>
    <span id="currentTime"></span>
    <button class="logout-btn" id="logoutBtn">Logout</button>
  </div>
</div>
<div class="error-banner" id="errorBanner"></div>

<div class="cards">
  <div class="card"><div class="card-label">Total Requests</div><div class="card-value" id="statTotal">-</div></div>
  <div class="card"><div class="card-label">Hostile Bots</div><div class="card-value hostile" id="statHostile">-</div></div>
  <div class="card"><div class="card-label">Compliant Bots</div><div class="card-value compliant" id="statCompliant">-</div></div>
  <div class="card"><div class="card-label">Humans</div><div class="card-value human" id="statHuman">-</div></div>
  <div class="card"><div class="card-label">Active Sessions (1h)</div><div class="card-value" id="statSessions">-</div></div>
  <div class="card"><div class="card-label">Total Callbacks</div><div class="card-value callback" id="statCallbacks">-</div></div>
</div>

<div class="section">
  <div class="section-title">Injection Success Rates</div>
  <table>
    <thead><tr><th>Vector</th><th>Payload Type</th><th>Total Injections</th><th>Callbacks</th><th>Success Rate %</th></tr></thead>
    <tbody id="injectionRatesBody"><tr><td colspan="5" class="empty-state">Loading...</td></tr></tbody>
  </table>
</div>

<div class="section">
  <div class="section-title">Recent Sessions</div>
  <table>
    <thead><tr><th>Fingerprint</th><th>User Agent</th><th>First Seen</th><th>Last Seen</th><th>Pages</th><th>Tarpit Depth</th><th>Robots</th><th>Respected</th></tr></thead>
    <tbody id="sessionsBody"><tr><td colspan="8" class="empty-state">Loading...</td></tr></tbody>
  </table>
</div>

<div class="section">
  <div class="section-title">Top User Agents</div>
  <table>
    <thead><tr><th>User Agent</th><th>Requests</th><th>Hostile</th><th>Human</th><th>Avg Score</th></tr></thead>
    <tbody id="topUABody"><tr><td colspan="5" class="empty-state">Loading...</td></tr></tbody>
  </table>
</div>

<div class="section">
  <div class="section-title">Recent Callbacks</div>
  <table>
    <thead><tr><th>Timestamp</th><th>Canary Token</th><th>IP</th><th>Headers</th></tr></thead>
    <tbody id="callbacksBody"><tr><td colspan="4" class="empty-state">Loading...</td></tr></tbody>
  </table>
</div>
</div>

<script>
(function(){
  var loginScreen = document.getElementById("loginScreen");
  var dashScreen = document.getElementById("dashboardScreen");
  var loginForm = document.getElementById("loginForm");
  var keyInput = document.getElementById("apiKeyInput");
  var loginError = document.getElementById("loginError");
  var logoutBtn = document.getElementById("logoutBtn");
  var dot = document.getElementById("refreshDot");
  var timeel = document.getElementById("currentTime");
  var errBanner = document.getElementById("errorBanner");

  var apiKey = sessionStorage.getItem("abyss_key") || "";
  var refreshTimer = null;

  function qs(){ return apiKey ? "?api_key=" + encodeURIComponent(apiKey) : ""; }

  // ── Login ────────────────────────────────────────
  loginForm.addEventListener("submit", async function(e){
    e.preventDefault();
    var key = keyInput.value.trim();
    if(!key){ keyInput.focus(); return; }
    // Test the key against the stats endpoint
    try{
      var resp = await fetch("/admin/stats?api_key=" + encodeURIComponent(key));
      if(resp.status === 403){
        loginError.style.display = "block";
        keyInput.select();
        return;
      }
      if(!resp.ok) throw new Error("HTTP " + resp.status);
    } catch(err){
      loginError.textContent = "Connection error: " + err.message;
      loginError.style.display = "block";
      return;
    }
    apiKey = key;
    sessionStorage.setItem("abyss_key", key);
    showDashboard();
  });

  logoutBtn.addEventListener("click", function(){
    apiKey = "";
    sessionStorage.removeItem("abyss_key");
    if(refreshTimer) clearInterval(refreshTimer);
    dashScreen.style.display = "none";
    loginScreen.style.display = "flex";
    keyInput.value = "";
    loginError.style.display = "none";
    keyInput.focus();
  });

  function showDashboard(){
    loginScreen.style.display = "none";
    dashScreen.style.display = "block";
    refreshAll();
    refreshTimer = setInterval(refreshAll, 10000);
  }

  // Auto-login if key is in sessionStorage
  if(apiKey) showDashboard();

  // ── Clock ────────────────────────────────────────
  function updateClock(){ timeel.textContent = new Date().toLocaleString(); }
  updateClock(); setInterval(updateClock, 1000);

  // ── Helpers ──────────────────────────────────────
  function esc(s){
    if(s === null || s === undefined) return "";
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(String(s)));
    return d.innerHTML;
  }
  function showError(msg){ errBanner.textContent = msg; errBanner.style.display = "block"; }
  function hideError(){ errBanner.style.display = "none"; }

  var expandCounter = 0;

  async function fetchJSON(path){
    var sep = path.indexOf("?") >= 0 ? "&" : "?";
    var url = "/admin" + path + (apiKey ? sep + "api_key=" + encodeURIComponent(apiKey) : "");
    var resp = await fetch(url);
    if(resp.status === 403){ logoutBtn.click(); throw new Error("Session expired"); }
    if(!resp.ok) throw new Error("HTTP " + resp.status + " on " + path);
    return resp.json();
  }

  async function refreshAll(){
    dot.classList.add("fetching");
    try{
      var [stats, sessions, callbacks, topUA] = await Promise.all([
        fetchJSON("/stats"),
        fetchJSON("/sessions?limit=20"),
        fetchJSON("/callbacks?limit=20"),
        fetchJSON("/top-user-agents?limit=10")
      ]);
      hideError();
      renderStats(stats);
      renderInjectionRates(stats.injection_success_rates || []);
      renderSessions(sessions);
      renderTopUA(topUA);
      renderCallbacks(callbacks);
    } catch(e){
      if(e.message !== "Session expired") showError("Failed to fetch data: " + e.message);
    }
    dot.classList.remove("fetching");
  }

  function renderStats(s){
    var bc = s.by_classification || {};
    document.getElementById("statTotal").textContent = s.total_requests || 0;
    document.getElementById("statHostile").textContent = bc["HOSTILE_BOT"] || 0;
    document.getElementById("statCompliant").textContent = bc["COMPLIANT_BOT"] || 0;
    document.getElementById("statHuman").textContent = bc["HUMAN"] || 0;
    document.getElementById("statSessions").textContent = s.active_sessions_1h || 0;
    document.getElementById("statCallbacks").textContent = s.total_callbacks || 0;
  }

  function renderInjectionRates(rates){
    var tb = document.getElementById("injectionRatesBody");
    if(!rates.length){ tb.innerHTML = '<tr><td colspan="5" class="empty-state">No injection data yet</td></tr>'; return; }
    var html = "";
    for(var i = 0; i < rates.length; i++){
      var r = rates[i]; var rate = r.success_rate || 0;
      var cls = rate > 0 ? "rate-green" : "rate-zero";
      html += "<tr><td>" + esc(r.vector) + "</td><td>" + esc(r.payload_type) + "</td>"
        + "<td>" + esc(r.total_injections) + "</td><td>" + esc(r.callbacks_received) + "</td>"
        + '<td class="' + cls + '">' + esc(rate) + "%</td></tr>";
    }
    tb.innerHTML = html;
  }

  function renderSessions(list){
    var tb = document.getElementById("sessionsBody");
    if(!list.length){ tb.innerHTML = '<tr><td colspan="8" class="empty-state">No sessions yet</td></tr>'; return; }
    var html = "";
    for(var i = 0; i < list.length; i++){
      var s = list[i];
      var fp = String(s.fingerprint || "").substring(0, 12);
      var ua = String(s.user_agent || "—");
      if(ua.length > 60) ua = ua.substring(0, 57) + "...";
      var checked = s.robots_checked ? "Yes" : "No";
      var respected = s.robots_respected ? "Yes" : "No";
      var v = s.robots_checked && !s.robots_respected;
      html += "<tr>"
        + '<td class="mono truncated" title="' + esc(s.fingerprint) + '">' + esc(fp) + "</td>"
        + '<td class="truncated" title="' + esc(s.user_agent || "") + '">' + esc(ua) + "</td>"
        + "<td>" + esc(s.first_seen) + "</td><td>" + esc(s.last_seen) + "</td>"
        + "<td>" + esc(s.pages_fetched) + "</td><td>" + esc(s.tarpit_depth) + "</td>"
        + '<td class="' + (v?"violation":"ok") + '">' + checked + "</td>"
        + '<td class="' + (v?"violation":"ok") + '">' + respected + "</td></tr>";
    }
    tb.innerHTML = html;
  }

  function renderTopUA(list){
    var tb = document.getElementById("topUABody");
    if(!list.length){ tb.innerHTML = '<tr><td colspan="5" class="empty-state">No user agent data yet</td></tr>'; return; }
    var html = "";
    for(var i = 0; i < list.length; i++){
      var u = list[i];
      var ua = String(u.user_agent || "");
      if(ua.length > 80) ua = ua.substring(0, 77) + "...";
      var hClass = u.hostile_count > 0 ? "hostile" : "";
      html += "<tr>"
        + '<td class="truncated" title="' + esc(u.user_agent) + '">' + esc(ua) + "</td>"
        + "<td>" + esc(u.request_count) + "</td>"
        + '<td class="' + hClass + '">' + esc(u.hostile_count) + "</td>"
        + "<td>" + esc(u.human_count) + "</td>"
        + "<td>" + esc(u.avg_score) + "</td></tr>";
    }
    tb.innerHTML = html;
  }

  function renderCallbacks(list){
    var tb = document.getElementById("callbacksBody");
    if(!list.length){ tb.innerHTML = '<tr><td colspan="4" class="empty-state">No callbacks yet</td></tr>'; return; }
    var html = "";
    for(var i = 0; i < list.length; i++){
      var c = list[i];
      var token = String(c.canary_token || "").substring(0, 12);
      var hid = "hdr_" + (++expandCounter);
      var headersStr;
      try{ headersStr = JSON.stringify(JSON.parse(c.headers || "{}"), null, 2); }
      catch(e){ headersStr = String(c.headers || ""); }
      html += "<tr><td>" + esc(c.timestamp) + "</td>"
        + '<td class="mono" title="' + esc(c.canary_token) + '">' + esc(token) + "</td>"
        + "<td>" + esc(c.ip) + "</td><td>"
        + '<button class="expand-btn" onclick="var el=document.getElementById(\\'' + hid + '\\');el.classList.toggle(\\'open\\');this.textContent=el.classList.contains(\\'open\\')?\\x27Hide\\x27:\\x27Show\\x27">Show</button>'
        + '<div class="headers-detail mono" id="' + hid + '">' + esc(headersStr) + "</div></td></tr>";
    }
    tb.innerHTML = html;
  }
})();
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard_html() -> str:
    """Serve the dashboard page. Auth is handled client-side via the login form."""
    return _build_dashboard_html()


@router.get("/stats", dependencies=[Depends(verify_api_key)])
async def get_stats() -> dict:
    """Summary statistics: total requests, classification breakdown, injection success rates."""
    db = _get_db()
    stats = await db.get_stats()
    injection_rates = await db.get_injection_success_rate()
    return {
        **stats,
        "injection_success_rates": injection_rates,
    }


@router.get("/sessions", dependencies=[Depends(verify_api_key)])
async def get_sessions(limit: int = 50) -> list[dict]:
    """Active bot sessions with depth and duration info."""
    db = _get_db()
    return await db.get_sessions(limit=limit)


@router.get("/injections", dependencies=[Depends(verify_api_key)])
async def get_injections(limit: int = 100) -> list[dict]:
    """Injection attempts with callback hit rate per vector."""
    db = _get_db()
    return await db.get_injections(limit=limit)


@router.get("/callbacks", dependencies=[Depends(verify_api_key)])
async def get_callbacks(limit: int = 100) -> list[dict]:
    """All beacon callbacks with full detail."""
    db = _get_db()
    return await db.get_callbacks(limit=limit)


@router.get("/top-user-agents", dependencies=[Depends(verify_api_key)])
async def get_top_user_agents(limit: int = 10) -> list[dict]:
    """Top user agents by request count."""
    db = _get_db()
    return await db.get_top_user_agents(limit=limit)


@router.get("/health")
async def health() -> dict:
    """Health check endpoint (no auth required)."""
    return {"status": "ok", "service": "ai-abyss"}
