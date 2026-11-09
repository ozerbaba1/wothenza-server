/**
 * KAMUI v3.0 Wothenza Cloudflare Worker Lisans Sunucusu
 * 
 * Özellikler:
 * - 7/24 Kesintisiz (0 uyku, 0 gecikme) Cloudflare Edge ağı.
 * - iOS uygulamasından gelen /wz_activate ve /wz_check isteklerini karşılar.
 * - Web Tabanlı Admin Paneli (/admin): Tarayıcıdan tek tıkla anahtar üret, HWID sıfırla, blokla.
 * - Kurulum: dash.cloudflare.com -> Workers & Pages -> Create Worker -> Bu kodu yapıştır -> Deploy!
 */

// Yönetici Şifresi (Admin paneline giriş için)
const ADMIN_PASSWORD = "wothenza_admin_2026";

// KV Storage bağlandıysa kullanılır, bağlanmadıysa Edge Memory Map kullanılır
const memoryKeys = new Map();

// Varsayılan Test / Başlangıç Anahtarları
function seedDefaultKeys() {
  if (memoryKeys.size === 0) {
    memoryKeys.set("WZ-MASTER-LIFETIME-VIP99", {
      key: "WZ-MASTER-LIFETIME-VIP99",
      plan: "lifetime",
      hwid: null,
      status: "active",
      expires_at: null,
      note: "Yönetici Anahtarı",
      created_at: new Date().toISOString()
    });
  }
}

// Rastgele Anahtar Üretici
function generateKey() {
  const chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
  const seg = () => Array.from({ length: 5 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  return `WZ-${seg()}-${seg()}-${seg()}`;
}

export default {
  async fetch(request, env, ctx) {
    seedDefaultKeys();
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS Headers
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, apikey, Authorization",
      "Content-Type": "application/json; charset=utf-8"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // -------------------------------------------------- 1. AKTİVASYON ---
    if (path === "/wz_activate" || path === "/api/activate" || path.endsWith("/rpc/wz_activate")) {
      if (request.method !== "POST") return new Response(JSON.stringify({ ok: false, err: "method_not_allowed" }), { status: 405, headers: corsHeaders });
      
      let body;
      try { body = await request.json(); } catch (e) { return new Response(JSON.stringify({ ok: false, err: "invalid_json" }), { status: 400, headers: corsHeaders }); }
      
      const p_key = (body.p_key || body.key || "").trim().toUpperCase();
      const p_hwid = (body.p_hwid || body.hwid || "").trim();

      if (!p_key) return new Response(JSON.stringify({ ok: false, err: "invalid" }), { headers: corsHeaders });

      let record = env.KEYS_KV ? JSON.parse(await env.KEYS_KV.get(p_key) || "null") : memoryKeys.get(p_key);
      if (!record) {
        return new Response(JSON.stringify({ ok: false, err: "invalid" }), { headers: corsHeaders });
      }

      if (record.status === "blocked") {
        return new Response(JSON.stringify({ ok: false, err: "blocked" }), { headers: corsHeaders });
      }

      // HWID Kontrolü
      if (record.status === "active" && record.hwid && record.hwid !== p_hwid) {
        return new Response(JSON.stringify({ ok: false, err: "hwid_mismatch" }), { headers: corsHeaders });
      }

      // Süre Kontrolü
      const now = new Date();
      if (record.expires_at && new Date(record.expires_at) < now) {
        return new Response(JSON.stringify({ ok: false, err: "expired" }), { headers: corsHeaders });
      }

      // İlk Aktivasyon
      if (record.status === "unused" || !record.hwid) {
        record.status = "active";
        record.hwid = p_hwid;
        record.activated_at = now.toISOString();

        if (record.plan === "trial") {
          record.expires_at = new Date(now.getTime() + 3 * 86400000).toISOString();
        } else if (record.plan === "week") {
          record.expires_at = new Date(now.getTime() + 7 * 86400000).toISOString();
        } else if (record.plan === "month") {
          record.expires_at = new Date(now.getTime() + 30 * 86400000).toISOString();
        } else {
          record.expires_at = null; // Lifetime
        }

        if (env.KEYS_KV) await env.KEYS_KV.put(p_key, JSON.stringify(record));
        else memoryKeys.set(p_key, record);
      }

      return new Response(JSON.stringify({
        ok: true,
        plan: record.plan,
        expires_at: record.expires_at
      }), { headers: corsHeaders });
    }

    // ------------------------------------------------ 2. YENİDEN KONTROL ---
    if (path === "/wz_check" || path === "/api/check" || path.endsWith("/rpc/wz_check")) {
      if (request.method !== "POST") return new Response(JSON.stringify({ ok: false }), { status: 405, headers: corsHeaders });
      
      let body;
      try { body = await request.json(); } catch (e) { return new Response(JSON.stringify({ ok: false }), { status: 400, headers: corsHeaders }); }
      
      const p_key = (body.p_key || body.key || "").trim().toUpperCase();
      const p_hwid = (body.p_hwid || body.hwid || "").trim();

      let record = env.KEYS_KV ? JSON.parse(await env.KEYS_KV.get(p_key) || "null") : memoryKeys.get(p_key);
      if (!record) return new Response(JSON.stringify({ ok: false, err: "invalid" }), { headers: corsHeaders });
      if (record.status === "blocked") return new Response(JSON.stringify({ ok: false, err: "blocked" }), { headers: corsHeaders });
      if (record.hwid && record.hwid !== p_hwid) return new Response(JSON.stringify({ ok: false, err: "hwid_mismatch" }), { headers: corsHeaders });
      if (record.expires_at && new Date(record.expires_at) < new Date()) return new Response(JSON.stringify({ ok: false, err: "expired" }), { headers: corsHeaders });

      return new Response(JSON.stringify({
        ok: true,
        plan: record.plan,
        expires_at: record.expires_at
      }), { headers: corsHeaders });
    }

    // ------------------------------------------------- 3. WEB ADMİN PANELİ ---
    if (path === "/admin") {
      const pass = url.searchParams.get("pass");
      if (pass !== ADMIN_PASSWORD) {
        return new Response(renderLoginHTML(), { headers: { "Content-Type": "text/html; charset=utf-8" } });
      }

      return new Response(renderAdminHTML(Array.from(memoryKeys.values()), pass), { headers: { "Content-Type": "text/html; charset=utf-8" } });
    }

    // Admin Aksiyonları: Anahtar Üret / HWID Sıfırla / Blokla
    if (path === "/admin/action") {
      const pass = url.searchParams.get("pass");
      if (pass !== ADMIN_PASSWORD) return new Response("Yetkisiz", { status: 403 });

      const form = await request.formData();
      const action = form.get("action");

      if (action === "generate") {
        const plan = form.get("plan") || "month";
        const count = parseInt(form.get("count") || "1", 10);
        const note = form.get("note") || "";

        for (let i = 0; i < count; i++) {
          const k = generateKey();
          const rec = {
            key: k,
            plan: plan,
            hwid: null,
            status: "unused",
            expires_at: null,
            note: note,
            created_at: new Date().toISOString()
          };
          if (env.KEYS_KV) await env.KEYS_KV.put(k, JSON.stringify(rec));
          else memoryKeys.set(k, rec);
        }
      } else if (action === "reset_hwid") {
        const k = form.get("key");
        let rec = env.KEYS_KV ? JSON.parse(await env.KEYS_KV.get(k) || "null") : memoryKeys.get(k);
        if (rec) {
          rec.hwid = null;
          if (env.KEYS_KV) await env.KEYS_KV.put(k, JSON.stringify(rec));
          else memoryKeys.set(k, rec);
        }
      } else if (action === "block") {
        const k = form.get("key");
        let rec = env.KEYS_KV ? JSON.parse(await env.KEYS_KV.get(k) || "null") : memoryKeys.get(k);
        if (rec) {
          rec.status = "blocked";
          if (env.KEYS_KV) await env.KEYS_KV.put(k, JSON.stringify(rec));
          else memoryKeys.set(k, rec);
        }
      }

      return Response.redirect(`${url.origin}/admin?pass=${pass}`, 302);
    }

    // Kök Dizin
    return new Response(JSON.stringify({
      service: "KAMUI v3.0 License Server",
      status: "online",
      community: "t.me/wothenza",
      time: new Date().toISOString()
    }), { headers: corsHeaders });
  }
};

// HTML Arayüzleri
function renderLoginHTML() {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>KAMUI VIP Admin</title>
  <style>body{background:#0a0a0b;color:#f4f4f2;font-family:-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
  .card{background:#131315;border:1px solid rgba(255,255,255,0.08);padding:32px;border-radius:18px;width:320px;text-align:center;}
  input{width:100%;box-sizing:border-box;padding:12px;background:#1b1b1e;border:1px solid rgba(255,255,255,0.1);color:#fff;border-radius:10px;margin:16px 0;font-size:14px;}
  button{width:100%;padding:12px;background:#ede8de;color:#0a0a0b;border:none;border-radius:10px;font-weight:600;cursor:pointer;}</style></head>
  <body><div class="card"><h2 style="margin:0 0 8px">KAMUI Admin</h2><p style="color:#8a8a8e;font-size:13px;margin:0">Wothenza VIP Yönetim Paneli</p>
  <form method="GET"><input type="password" name="pass" placeholder="Yönetici Şifresi" required><button type="submit">Giriş Yap</button></form></div></body></html>`;
}

function renderAdminHTML(keys, pass) {
  const rows = keys.map(k => `<tr>
    <td style="font-family:monospace;color:#ede8de;font-weight:bold">${k.key}</td>
    <td><span style="background:#1b1b1e;padding:4px 8px;border-radius:6px">${k.plan.toUpperCase()}</span></td>
    <td><span style="color:${k.status==='active'?'#30d158':(k.status==='blocked'?'#ff453a':'#8a8a8e')}">${k.status.toUpperCase()}</span></td>
    <td style="font-family:monospace;font-size:12px">${k.hwid ? k.hwid.substring(0,8)+'...' : '<span style="color:#56565b">Bağlı Değil</span>'}</td>
    <td style="font-size:12px;color:#8a8a8e">${k.expires_at ? new Date(k.expires_at).toLocaleDateString('tr-TR') : 'Ömür Boyu'}</td>
    <td style="font-size:12px;color:#8a8a8e">${k.note || '-'}</td>
    <td>
      <form method="POST" action="/admin/action?pass=${pass}" style="display:inline">
        <input type="hidden" name="action" value="reset_hwid"><input type="hidden" name="key" value="${k.key}">
        <button style="background:#282824;color:#ede8de;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px">HWID Sıfırla</button>
      </form>
      <form method="POST" action="/admin/action?pass=${pass}" style="display:inline;margin-left:4px">
        <input type="hidden" name="action" value="block"><input type="hidden" name="key" value="${k.key}">
        <button style="background:rgba(255,69,58,0.2);color:#ff453a;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px">Blokla</button>
      </form>
    </td>
  </tr>`).join("");

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>KAMUI VIP Lisans Paneli</title>
  <style>body{background:#0a0a0b;color:#f4f4f2;font-family:-apple-system,sans-serif;margin:0;padding:24px;}
  .container{max-width:1000px;margin:0 auto;}
  .card{background:#131315;border:1px solid rgba(255,255,255,0.08);padding:24px;border-radius:18px;margin-bottom:24px;}
  table{width:100%;border-collapse:collapse;font-size:14px;margin-top:16px;}
  th,td{padding:12px 10px;border-bottom:1px solid rgba(255,255,255,0.06);text-align:left;}
  th{color:#8a8a8e;font-size:12px;font-family:monospace;letter-spacing:1px;}
  input,select{background:#1b1b1e;border:1px solid rgba(255,255,255,0.1);color:#fff;padding:10px;border-radius:8px;font-size:14px;}
  .btn{background:#ede8de;color:#0a0a0b;border:none;padding:10px 18px;border-radius:8px;font-weight:600;cursor:pointer;}</style></head>
  <body><div class="container">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
      <div><h1 style="margin:0;font-size:28px">KAMUI v3.0 VIP</h1><p style="margin:4px 0 0;color:#8a8a8e;font-size:13px">Wothenza Canlı Lisans Sunucusu</p></div>
      <a href="https://t.me/wothenza" target="_blank" style="color:#ede8de;text-decoration:none;font-size:14px;background:#131315;border:1px solid rgba(255,255,255,0.1);padding:8px 16px;border-radius:10px">t.me/wothenza ↗</a>
    </div>

    <div class="card">
      <h3 style="margin:0 0 16px;font-size:16px">Yeni Anahtar Üret</h3>
      <form method="POST" action="/admin/action?pass=${pass}" style="display:flex;gap:12px;flex-wrap:wrap">
        <input type="hidden" name="action" value="generate">
        <select name="plan"><option value="month">1 Aylık</option><option value="week">1 Haftalık</option><option value="trial">3 Günlük Deneme</option><option value="lifetime">Ömür Boyu (Lifetime)</option></select>
        <input type="number" name="count" value="1" min="1" max="50" style="width:70px">
        <input type="text" name="note" placeholder="Müşteri Notu (Örn: @ali)" style="flex:1">
        <button type="submit" class="btn">Üret ve Kaydet</button>
      </form>
    </div>

    <div class="card">
      <h3 style="margin:0 0 8px;font-size:16px">Kayıtlı Anahtarlar (${keys.length})</h3>
      <table>
        <thead><tr><th>ANAHTAR</th><th>PLAN</th><th>DURUM</th><th>HWID</th><th>BİTİŞ</th><th>NOT</th><th>İŞLEMLER</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  </div></body></html>`;
}

