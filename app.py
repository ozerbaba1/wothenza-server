#!/usr/bin/env python3
"""
KAMUI v3.0 Wothenza Lisans Sunucusu (Zero-Dependency — Sıfır Kurulum)
Python standart kütüphanesiyle (http.server + sqlite3) çalışır; pip veya ek paket GEREKTİRMEZ.
Render, Koyeb, Railway, VPS veya doğrudan Windows'ta anında çalışır.
"""

import os
import sys
import json
import sqlite3
import secrets
import threading
import time
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

PORT = int(os.environ.get("PORT", 5000))
DB_PATH = os.environ.get("DB_PATH", "keys.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "wothenza_admin_2026")
SELF_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL DEFAULT 'month',
                hwid TEXT,
                status TEXT NOT NULL DEFAULT 'unused',
                created_at TEXT NOT NULL,
                activated_at TEXT,
                expires_at TEXT,
                note TEXT
            )
        """)
        db.execute("""
            INSERT OR IGNORE INTO keys (key, plan, status, created_at, note)
            VALUES ('WZ-MASTER-LIFETIME-VIP99', 'lifetime', 'unused', datetime('now'), 'Master Test Key')
        """)
        db.commit()

init_db()

# Render Anti-Sleep Worker (10 dakikada bir kendini pingler)
def anti_sleep_worker():
    while True:
        time.sleep(600)
        target = SELF_URL or f"http://127.0.0.1:{PORT}"
        try:
            req = urllib.request.Request(f"{target}/ping", headers={"User-Agent": "SelfPing/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception:
            pass

threading.Thread(target=anti_sleep_worker, daemon=True).start()

def generate_key():
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    seg = lambda: "".join(secrets.choice(chars) for _ in range(5))
    return f"WZ-{seg()}-{seg()}-{seg()}"

class LicenseHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, apikey, Authorization")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, apikey, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/ping":
            self.send_json({"status": "alive", "time": datetime.utcnow().isoformat()})
            return

        if path == "/admin":
            pass_val = query.get("pass", [""])[0]
            if pass_val != ADMIN_PASSWORD:
                self.send_html(self.render_login())
                return

            with get_db() as db:
                rows = db.execute("SELECT * FROM keys ORDER BY id DESC").fetchall()
            self.send_html(self.render_admin(rows, pass_val))
            return

        self.send_json({
            "service": "KAMUI v3.0 Wothenza License API",
            "status": "online",
            "community": "t.me/wothenza",
            "time": datetime.utcnow().isoformat()
        })

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b""

        # 1. Aktivasyon (/wz_activate, /api/activate, /rest/v1/rpc/wz_activate)
        if path in ["/wz_activate", "/api/activate", "/rest/v1/rpc/wz_activate"]:
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                self.send_json({"ok": False, "err": "invalid_json"}, 400)
                return

            key = (data.get("p_key") or data.get("key") or "").strip().upper()
            hwid = (data.get("p_hwid") or data.get("hwid") or "").strip()

            if not key:
                self.send_json({"ok": False, "err": "invalid"})
                return

            now = datetime.utcnow()
            with get_db() as db:
                row = db.execute("SELECT * FROM keys WHERE key = ?", (key,)).fetchone()
                if not row:
                    self.send_json({"ok": False, "err": "invalid"})
                    return

                if row["status"] == "blocked":
                    self.send_json({"ok": False, "err": "blocked"})
                    return

                if row["status"] == "active" and row["hwid"] and row["hwid"] != hwid:
                    self.send_json({"ok": False, "err": "hwid_mismatch"})
                    return

                if row["expires_at"]:
                    exp = datetime.fromisoformat(row["expires_at"].replace("Z", ""))
                    if exp < now:
                        self.send_json({"ok": False, "err": "expired"})
                        return

                if row["status"] == "unused" or not row["hwid"]:
                    plan = row["plan"]
                    if plan == "trial":
                        exp_date = now + timedelta(days=3)
                    elif plan == "week":
                        exp_date = now + timedelta(days=7)
                    elif plan == "month":
                        exp_date = now + timedelta(days=30)
                    else:
                        exp_date = None

                    exp_str = exp_date.isoformat() + "Z" if exp_date else None
                    now_str = now.isoformat() + "Z"

                    db.execute("""
                        UPDATE keys SET status = 'active', hwid = ?, activated_at = ?, expires_at = ?
                        WHERE id = ?
                    """, (hwid, now_str, exp_str, row["id"]))
                    db.commit()

                    self.send_json({"ok": True, "plan": plan, "expires_at": exp_str})
                    return

                self.send_json({"ok": True, "plan": row["plan"], "expires_at": row["expires_at"]})
            return

        # 2. Yeniden Kontrol (/wz_check, /api/check, /rest/v1/rpc/wz_check)
        if path in ["/wz_check", "/api/check", "/rest/v1/rpc/wz_check"]:
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                self.send_json({"ok": False, "err": "invalid_json"}, 400)
                return

            key = (data.get("p_key") or data.get("key") or "").strip().upper()
            hwid = (data.get("p_hwid") or data.get("hwid") or "").strip()

            with get_db() as db:
                row = db.execute("SELECT * FROM keys WHERE key = ?", (key,)).fetchone()
                if not row:
                    self.send_json({"ok": False, "err": "invalid"})
                    return
                if row["status"] == "blocked":
                    self.send_json({"ok": False, "err": "blocked"})
                    return
                if row["hwid"] and row["hwid"] != hwid:
                    self.send_json({"ok": False, "err": "hwid_mismatch"})
                    return
                if row["expires_at"]:
                    exp = datetime.fromisoformat(row["expires_at"].replace("Z", ""))
                    if exp < datetime.utcnow():
                        self.send_json({"ok": False, "err": "expired"})
                        return
                self.send_json({"ok": True, "plan": row["plan"], "expires_at": row["expires_at"]})
            return

        # 3. Admin Aksiyonları
        if path == "/admin/action":
            query = urllib.parse.parse_qs(parsed.query)
            pass_val = query.get("pass", [""])[0]
            if pass_val != ADMIN_PASSWORD:
                self.send_response(403)
                self.end_headers()
                return

            form = urllib.parse.parse_qs(raw_body.decode("utf-8"))
            action = form.get("action", [""])[0]

            with get_db() as db:
                if action == "generate":
                    plan = form.get("plan", ["month"])[0]
                    count = int(form.get("count", ["1"])[0])
                    note = form.get("note", [""])[0]
                    now_str = datetime.utcnow().isoformat() + "Z"
                    for _ in range(count):
                        db.execute("INSERT INTO keys (key, plan, status, created_at, note) VALUES (?, ?, 'unused', ?, ?)",
                                   (generateKey(), plan, now_str, note))
                    db.commit()
                elif action == "reset_hwid":
                    k = form.get("key", [""])[0]
                    db.execute("UPDATE keys SET hwid = NULL WHERE key = ?", (k,))
                    db.commit()
                elif action == "block":
                    k = form.get("key", [""])[0]
                    db.execute("UPDATE keys SET status = 'blocked' WHERE key = ?", (k,))
                    db.commit()

            self.send_response(302)
            self.send_header("Location", f"/admin?pass={pass_val}")
            self.end_headers()
            return

        self.send_json({"ok": False, "err": "not_found"}, 404)

    def render_login(self):
        return """<!DOCTYPE html><html><head><meta charset="utf-8"><title>KAMUI Admin</title>
        <style>body{background:#0a0a0b;color:#f4f4f2;font-family:-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
        .card{background:#131315;border:1px solid rgba(255,255,255,0.08);padding:32px;border-radius:18px;width:320px;text-align:center;}
        input{width:100%;box-sizing:border-box;padding:12px;background:#1b1b1e;border:1px solid rgba(255,255,255,0.1);color:#fff;border-radius:10px;margin:16px 0;font-size:14px;}
        button{width:100%;padding:12px;background:#ede8de;color:#0a0a0b;border:none;border-radius:10px;font-weight:600;cursor:pointer;}</style></head>
        <body><div class="card"><h2 style="margin:0 0 8px">KAMUI Admin</h2><p style="color:#8a8a8e;font-size:13px;margin:0">Wothenza VIP Yönetim Paneli</p>
        <form method="GET"><input type="password" name="pass" placeholder="Yönetici Şifresi" required><button type="submit">Giriş Yap</button></form></div></body></html>"""

    def render_admin(self, keys, pass_val):
        rows = ""
        for k in keys:
            st = k["status"]
            st_color = "#30d158" if st == "active" else ("#ff453a" if st == "blocked" else "#8a8a8e")
            hwid_text = (k["hwid"][:8] + "...") if k["hwid"] else '<span style="color:#56565b">Bağlı Değil</span>'
            exp_text = k["expires_at"][:10] if k["expires_at"] else "Ömür Boyu"
            rows += f"""<tr>
                <td style="font-family:monospace;color:#ede8de;font-weight:bold">{k['key']}</td>
                <td><span style="background:#1b1b1e;padding:4px 8px;border-radius:6px">{k['plan'].upper()}</span></td>
                <td><span style="color:{st_color}">{st.upper()}</span></td>
                <td style="font-family:monospace">{hwid_text}</td>
                <td style="color:#8a8a8e">{exp_text}</td>
                <td style="color:#8a8a8e">{k['note'] or '-'}</td>
                <td>
                    <form method="POST" action="/admin/action?pass={pass_val}" style="display:inline">
                        <input type="hidden" name="action" value="reset_hwid"><input type="hidden" name="key" value="{k['key']}">
                        <button style="background:#282824;color:#ede8de;border:none;padding:4px 8px;border-radius:6px;cursor:pointer">HWID Sıfırla</button>
                    </form>
                    <form method="POST" action="/admin/action?pass={pass_val}" style="display:inline;margin-left:4px">
                        <input type="hidden" name="action" value="block"><input type="hidden" name="key" value="{k['key']}">
                        <button style="background:rgba(255,69,58,0.2);color:#ff453a;border:none;padding:4px 8px;border-radius:6px;cursor:pointer">Blokla</button>
                    </form>
                </td>
            </tr>"""

        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>KAMUI VIP Paneli</title>
        <style>body{{background:#0a0a0b;color:#f4f4f2;font-family:-apple-system,sans-serif;margin:0;padding:24px;}}
        .container{{max-width:1000px;margin:0 auto;}}
        .card{{background:#131315;border:1px solid rgba(255,255,255,0.08);padding:24px;border-radius:18px;margin-bottom:24px;}}
        table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:16px;}}
        th,td{{padding:12px 10px;border-bottom:1px solid rgba(255,255,255,0.06);text-align:left;}}
        th{{color:#8a8a8e;font-size:12px;font-family:monospace;letter-spacing:1px;}}
        input,select{{background:#1b1b1e;border:1px solid rgba(255,255,255,0.1);color:#fff;padding:10px;border-radius:8px;font-size:14px;}}
        .btn{{background:#ede8de;color:#0a0a0b;border:none;padding:10px 18px;border-radius:8px;font-weight:600;cursor:pointer;}}</style></head>
        <body><div class="container">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
                <div><h1 style="margin:0">KAMUI v3.0 VIP</h1><p style="color:#8a8a8e;margin:4px 0">Wothenza Canlı Lisans Sunucusu</p></div>
                <a href="https://t.me/wothenza" target="_blank" style="color:#ede8de;text-decoration:none;background:#131315;border:1px solid rgba(255,255,255,0.1);padding:8px 16px;border-radius:10px">t.me/wothenza ↗</a>
            </div>
            <div class="card">
                <h3 style="margin:0 0 16px">Yeni Anahtar Üret</h3>
                <form method="POST" action="/admin/action?pass={pass_val}" style="display:flex;gap:12px;flex-wrap:wrap">
                    <input type="hidden" name="action" value="generate">
                    <select name="plan"><option value="month">1 Aylık</option><option value="week">1 Haftalık</option><option value="trial">3 Günlük Deneme</option><option value="lifetime">Ömür Boyu</option></select>
                    <input type="number" name="count" value="1" min="1" max="50" style="width:70px">
                    <input type="text" name="note" placeholder="Müşteri Notu (Örn: @ali)" style="flex:1">
                    <button type="submit" class="btn">Üret ve Kaydet</button>
                </form>
            </div>
            <div class="card">
                <h3 style="margin:0 0 8px">Kayıtlı Anahtarlar ({len(keys)})</h3>
                <table><thead><tr><th>ANAHTAR</th><th>PLAN</th><th>DURUM</th><th>HWID</th><th>BİTİŞ</th><th>NOT</th><th>İŞLEMLER</th></tr></thead>
                <tbody>{rows}</tbody></table>
            </div>
        </div></body></html>"""

def run():
    server = HTTPServer(("0.0.0.0", PORT), LicenseHandler)
    print(f"[*] KAMUI License Server running on http://0.0.0.0:{PORT}")
    print(f"[*] Admin Panel: http://localhost:{PORT}/admin?pass={ADMIN_PASSWORD}")
    server.serve_forever()

if __name__ == "__main__":
    run()
