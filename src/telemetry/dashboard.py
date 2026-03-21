# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Admin dashboard API endpoints for telemetry and monitoring

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
    if not _api_key:
        return
    key = request.headers.get("x-api-key", "") or request.query_params.get("api_key", "")
    if key != _api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


def _build_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Abyss — Dashboard</title>
<style>
body{background:#111;color:#999;font-family:monospace;font-size:13px;line-height:1.5;margin:0;padding:0}
a{color:#c00}
h1{color:#c00;font-weight:normal;font-size:16px}

.login-wrap{display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{border:1px solid #333;padding:2em;width:280px;text-align:center}
.login-box h1{margin-bottom:2px}
.login-box .sub{color:#666;font-size:12px;margin-bottom:1.5em}
.login-box input{width:100%;padding:6px;background:#111;border:1px solid #333;color:#ccc;font-family:monospace;margin-bottom:8px}
.login-box button{width:100%;padding:6px;background:#c00;border:none;color:#000;font-weight:bold;cursor:pointer;font-family:monospace}
.login-error{color:#c00;font-size:12px;margin-top:6px;display:none}

.dashboard{display:none;padding:16px 20px;max-width:1100px;margin:0 auto}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;border-bottom:1px solid #222;padding-bottom:10px}
.header-right{font-size:12px;color:#666;display:flex;align-items:center;gap:10px}
.logout-btn{background:none;border:1px solid #333;padding:1px 8px;color:#666;font-size:11px;cursor:pointer;font-family:monospace}
.refresh-indicator{display:inline-block;width:6px;height:6px;background:#0a0;margin-right:4px;vertical-align:middle}
.refresh-indicator.fetching{background:#a80}

.cards{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}
.card{border:1px solid #222;padding:10px 14px;min-width:130px}
.card-label{font-size:10px;color:#666;text-transform:uppercase}
.card-value{font-size:22px;font-weight:bold;color:#ccc}
.card-value.hostile{color:#c00}
.card-value.compliant{color:#a80}
.card-value.human{color:#0a0}
.card-value.callback{color:#c00}

.section{margin-bottom:20px}
.section-title{font-size:11px;color:#666;text-transform:uppercase;margin-bottom:6px;border-bottom:1px solid #222;padding-bottom:4px}
table{width:100%;border-collapse:collapse}
thead th{text-align:left;padding:4px 8px;font-size:10px;color:#666;text-transform:uppercase;font-weight:normal;border-bottom:1px solid #222}
tbody td{padding:4px 8px;border-bottom:1px solid #1a1a1a;font-size:12px}
tbody tr:hover{background:#1a1a1a}
.rate-green{color:#0a0;font-weight:bold}
.rate-zero{color:#444}
.violation{color:#c00}
.ok{color:#666}
.mono{font-size:11px}
.truncated{max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

.expand-btn{background:#1a1a1a;color:#666;border:1px solid #333;padding:1px 6px;font-size:10px;cursor:pointer;font-family:monospace}
.headers-detail{display:none;margin-top:4px;padding:6px;border:1px solid #222;font-size:11px;white-space:pre-wrap;word-break:break-all;max-height:180px;overflow-y:auto;color:#666}
.headers-detail.open{display:block}

.empty-state{padding:14px;text-align:center;color:#444}
.error-banner{border:1px solid #c00;color:#c00;padding:6px 10px;margin-bottom:12px;display:none}
</style>
</head>
<body>

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

  loginForm.addEventListener("submit", async function(e){
    e.preventDefault();
    var key = keyInput.value.trim();
    if(!key){ keyInput.focus(); return; }
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

  if(apiKey) showDashboard();

  function updateClock(){ timeel.textContent = new Date().toLocaleString(); }
  updateClock(); setInterval(updateClock, 1000);

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
    return _build_dashboard_html()


@router.get("/stats", dependencies=[Depends(verify_api_key)])
async def get_stats() -> dict:
    db = _get_db()
    stats = await db.get_stats()
    injection_rates = await db.get_injection_success_rate()
    return {
        **stats,
        "injection_success_rates": injection_rates,
    }


@router.get("/sessions", dependencies=[Depends(verify_api_key)])
async def get_sessions(limit: int = 50) -> list[dict]:
    db = _get_db()
    return await db.get_sessions(limit=limit)


@router.get("/injections", dependencies=[Depends(verify_api_key)])
async def get_injections(limit: int = 100) -> list[dict]:
    db = _get_db()
    return await db.get_injections(limit=limit)


@router.get("/callbacks", dependencies=[Depends(verify_api_key)])
async def get_callbacks(limit: int = 100) -> list[dict]:
    db = _get_db()
    return await db.get_callbacks(limit=limit)


@router.get("/top-user-agents", dependencies=[Depends(verify_api_key)])
async def get_top_user_agents(limit: int = 10) -> list[dict]:
    db = _get_db()
    return await db.get_top_user_agents(limit=limit)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "ai-abyss"}
