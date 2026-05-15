import { NextRequest, NextResponse } from "next/server";

const GEMINI_ORIGIN = "https://generativelanguage.googleapis.com";
const PROXY_SECRET = process.env.GEMINI_PROXY_SECRET || "";

export const runtime = "nodejs"; // Serverless (US East iad1), NOT edge

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyToGemini(request, await params);
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyToGemini(request, await params);
}

async function proxyToGemini(
  request: NextRequest,
  { path }: { path: string[] }
) {
  // Optional: verify shared secret to prevent abuse
  if (PROXY_SECRET) {
    const authHeader = request.headers.get("x-proxy-secret");
    if (authHeader !== PROXY_SECRET) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
  }

  const targetPath = path.join("/");
  const url = new URL(request.url);
  const targetUrl = `${GEMINI_ORIGIN}/${targetPath}${url.search}`;

  // Only forward essential headers — strip all proxy/location headers
  // so Google sees Vercel's US IP, not the original caller's IP
  const headers = new Headers();
  const ALLOWED_HEADERS = [
    "content-type",
    "x-goog-api-key",
    "x-goog-api-client",
    "authorization",
    "accept",
    "accept-encoding",
    "user-agent",
  ];
  for (const key of ALLOWED_HEADERS) {
    const value = request.headers.get(key);
    if (value) {
      headers.set(key, value);
    }
  }

  try {
    const body =
      request.method === "POST" ? await request.arrayBuffer() : undefined;

    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
    });

    const responseHeaders = new Headers();
    for (const [key, value] of response.headers.entries()) {
      if (!["transfer-encoding", "content-encoding"].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    }

    const responseBody = await response.arrayBuffer();
    return new NextResponse(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Gemini proxy error:", error);
    return NextResponse.json(
      { error: "Proxy error", detail: String(error) },
      { status: 502 }
    );
  }
}
