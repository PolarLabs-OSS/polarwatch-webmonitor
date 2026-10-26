"""PolarWatch Sites — lightweight, database-free website monitoring.

No mining, wallets, email sending, telemetry collection, server, or licensing.
Only user-selected URLs are contacted when monitoring is enabled.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

APP_NAME = "PolarWatch"
USER_AGENT = "PolarWatch/2.0 (local website diagnostics)"
SECURITY_HEADERS = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy",
}

def state_path():
    """A plain JSON list of URLs; no database, no monitoring history on disk."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "PolarLabs" / APP_NAME / "sites.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "polarlabs" / APP_NAME.lower() / "sites.json"

def normalize_url(raw):
    raw = str(raw).strip()
    if not raw:
        raise ValueError("Inserisci l'indirizzo del sito.")
    if "://" not in raw:
        raw = "https://" + raw
    parts = urllib.parse.urlsplit(raw)
    if parts.scheme.lower() not in ("https", "http") or not parts.hostname:
        raise ValueError("Utilizza un indirizzo http:// oppure https:// valido.")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Non inserire username o password nell'indirizzo.")
    try:
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError("Porta non valida.")
    except ValueError as exc:
        raise ValueError("Porta non valida.") from exc
    if len(raw) > 1800 or any(ch.isspace() for ch in raw):
        raise ValueError("L'indirizzo contiene caratteri non validi o è troppo lungo.")
    return raw

def new_site(name, url):
    url = normalize_url(url)
    name = str(name).strip() or urllib.parse.urlsplit(url).hostname or "Sito web"
    if len(name) > 65:
        raise ValueError("Nome troppo lungo (massimo 65 caratteri).")
    return {"id": uuid.uuid4().hex[:12], "name": name, "url": url}

def load_sites(path=None):
    path = Path(path) if path is not None else state_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as exc:
        raise ValueError("Elenco siti non leggibile. Verifica sites.json; non è stato sovrascritto.") from exc
    if not isinstance(data, list):
        raise ValueError("Formato sites.json non valido.")
    result, seen = [], set()
    for row in data[:150]:
        if not isinstance(row, dict):
            continue
        try:
            url = normalize_url(row.get("url", ""))
        except ValueError:
            continue
        if url.casefold() in seen:
            continue
        seen.add(url.casefold())
        entry = new_site(row.get("name") or "", url)
        identifier = row.get("id")
        if isinstance(identifier, str) and 1 <= len(identifier) <= 48:
            entry["id"] = identifier
        result.append(entry)
    return result

def save_sites(sites, path=None):
    path = Path(path) if path is not None else state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = [{"id": s["id"], "name": s["name"], "url": normalize_url(s["url"])}
             for s in sites]
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)

def _dns_ips(hostname, port):
    answers = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    return list(dict.fromkeys(a[4][0] for a in answers))[:6]

def _tls_details(hostname, port, timeout):
    context = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=hostname) as sock:
            cert = sock.getpeercert()
            not_after = cert.get("notAfter")
            remaining = int((ssl.cert_time_to_seconds(not_after) - time.time()) // 86400) if not_after else None
            return {
                "tls": sock.version() or "—",
                "cipher": (sock.cipher() or ("—",))[0],
                "ssl_days": remaining,
                "ssl_until": not_after or "—",
            }

def probe_site(site, timeout=8):
    """Return diagnostics; DNS/TLS inspections are read-only and never send credentials."""
    site_url = normalize_url(site["url"])
    start = time.monotonic()
    original = urllib.parse.urlsplit(site_url)
    result = {
        "id": site["id"], "name": site["name"], "url": site_url,
        "state": "DOWN", "code": None, "latency": None,
        "ttfb": None, "dns_ms": None, "dns": [],
        "checked": datetime.now().astimezone().strftime("%H:%M:%S"),
        "final_url": site_url, "redirect": False,
        "ssl_days": None, "ssl_until": "—", "tls": "—", "cipher": "—",
        "server": "—", "type": "—", "security_headers": {},
        "error": "", "notes": [],
    }
    try:
        begin = time.monotonic()
        result["dns"] = _dns_ips(original.hostname, original.port or (443 if original.scheme == "https" else 80))
        result["dns_ms"] = round((time.monotonic() - begin) * 1000)
    except (OSError, ValueError) as exc:
        result["notes"].append("DNS: " + str(exc)[:100])

    headers = {}
    begin = time.monotonic()
    try:
        req = urllib.request.Request(site_url, headers={"User-Agent": USER_AGENT}, method="GET")
        try:
            response = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            result["ttfb"] = round((time.monotonic() - begin) * 1000)
            result["code"] = response.status
            result["final_url"] = response.geturl()
            result["redirect"] = result["final_url"] != site_url
            headers = {k.lower(): v for k, v in response.headers.items()}
            response.read(512)
        result["latency"] = round((time.monotonic() - begin) * 1000)
        result["state"] = "UP" if 200 <= result["code"] < 400 else "DOWN"
        if result["state"] == "DOWN":
            result["error"] = f"Risposta HTTP {result['code']}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        result["latency"] = round((time.monotonic() - begin) * 1000)
        result["error"] = f"{type(exc).__name__}: {exc}"[:180]
    except Exception as exc:
        result["error"] = f"Errore richiesta: {type(exc).__name__}: {exc}"[:180]

    result["server"] = headers.get("server", "—")[:110]
    result["type"] = headers.get("content-type", "—")[:110]
    result["security_headers"] = {
        label: bool(headers.get(key)) for key, label in SECURITY_HEADERS.items()
    }

    final = urllib.parse.urlsplit(result["final_url"])
    if final.scheme == "https" and final.hostname:
        try:
            result.update(_tls_details(final.hostname, final.port or 443, timeout))
            if result["ssl_days"] is not None and result["ssl_days"] <= 14:
                result["notes"].append("Certificato TLS prossimo alla scadenza" if result["ssl_days"] >= 0
                                       else "Certificato TLS scaduto")
        except (OSError, ssl.SSLError, ValueError, TypeError) as exc:
            result["notes"].append("TLS: verifica aggiuntiva non riuscita (" + type(exc).__name__ + ")")
    elif final.scheme == "http":
        result["notes"].append("HTTP non cifrato (HTTPS consigliato)")

    result["elapsed"] = round((time.monotonic() - start) * 1000)
    return result
