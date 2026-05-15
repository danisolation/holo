/**
 * Cloudflare Worker — Gemini API Proxy
 * Forwards requests from geo-restricted regions to Google Gemini API.
 * Deploy this worker, then set GEMINI_PROXY_URL in your backend env.
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok", proxy: "gemini" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Forward everything else to Gemini API
    const targetUrl = `https://generativelanguage.googleapis.com${url.pathname}${url.search}`;

    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("cf-connecting-ip");
    headers.delete("cf-ipcountry");
    headers.delete("cf-ray");

    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method !== "GET" ? request.body : undefined,
    });

    // Pass through response with CORS
    const respHeaders = new Headers(response.headers);
    respHeaders.set("Access-Control-Allow-Origin", "*");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: respHeaders,
    });
  },
};
