interface Env {
  DEPLOY_URL: string;
  SECURE_GET_URL: string;
  CREATE_USER_URL: string;
  CLOUDLAUNCH_WORKER_SECRET: string;
}

const ROUTES = {
  "/api/deploy": "DEPLOY_URL",
  "/api/secureget": "SECURE_GET_URL",
  "/api/createuser": "CREATE_USER_URL",
} as const;

const ALLOWED_ORIGINS = new Set([
  "https://gocloudlaunch.com",
  "https://www.gocloudlaunch.com",
  "http://localhost:3000",
  "http://127.0.0.1:3000",
]);

const WORKER_SECRET_HEADER = "x-cloudlaunch-worker-secret";
const WORKER_RESPONSE_HEADER = "x-cloudlaunch-worker";

type RoutePath = keyof typeof ROUTES;
type EnvUrlKey = (typeof ROUTES)[RoutePath];

function getCorsHeaders(request: Request) {
  const origin = request.headers.get("Origin") || "";
  const allowedOrigin = ALLOWED_ORIGINS.has(origin) ? origin : "https://gocloudlaunch.com";

  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function withCors(response: Response, request: Request) {
  const headers = new Headers(response.headers);
  const corsHeaders = getCorsHeaders(request);
  headers.set(WORKER_RESPONSE_HEADER, "cloudlaunch-api");

  for (const [headerName, headerValue] of Object.entries(corsHeaders)) {
    headers.set(headerName, headerValue);
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function jsonResponse(body: unknown, status: number, request: Request) {
  return withCors(
    new Response(JSON.stringify(body), {
      status,
      headers: {
        "Content-Type": "application/json",
      },
    }),
    request,
  );
}

function getUpstreamUrl(pathname: string, env: Env) {
  const envKey = ROUTES[pathname as RoutePath] as EnvUrlKey | undefined;
  if (!envKey) {
    return null;
  }

  const url = env[envKey];
  return url ? new URL(url) : null;
}

async function proxyToLambda(request: Request, env: Env) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = getUpstreamUrl(requestUrl.pathname, env);

  if (!upstreamUrl) {
    return jsonResponse({ error: "Not found" }, 404, request);
  }

  if (!env.CLOUDLAUNCH_WORKER_SECRET) {
    return jsonResponse({ error: "Worker secret is not configured" }, 500, request);
  }

  upstreamUrl.search = requestUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("Host");
  headers.set(WORKER_SECRET_HEADER, env.CLOUDLAUNCH_WORKER_SECRET);

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
  }

  const upstreamResponse = await fetch(upstreamUrl.toString(), init);
  return withCors(upstreamResponse, request);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return withCors(new Response(null, { status: 204 }), request);
    }

    return proxyToLambda(request, env);
  },
};
