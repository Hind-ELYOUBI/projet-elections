// Recoit une anomalie (POST JSON) et l'envoie dans le groupe Telegram
export default {
  async fetch(req, env) {
    if (req.method !== "POST" || req.headers.get("x-secret") !== env.SECRET)
      return new Response("interdit", { status: 403 });
    const a = await req.json();
    const text = `⚠️ ANOMALIE ÉLECTORALE\nType : ${a.type}\nBureau : ${a.bureau_id}\n${a.details}\nDétectée : ${a.created_at}`;
    const r = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: env.CHAT_ID, text }),
    });
    return new Response(r.ok ? "ok" : await r.text(), { status: r.ok ? 200 : 502 });
  },
};
