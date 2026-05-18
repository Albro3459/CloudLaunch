# CloudLaunch API Worker

Cloudflare Worker that routes `gocloudlaunch.com/api/*` requests to the existing AWS Lambda Function URLs.

## Routes

```text
/api/deploy     -> Deploy Lambda Function URL
/api/secureget  -> SecureGet Lambda Function URL
/api/createuser -> CreateUser Lambda Function URL
```

The Worker is configured for both:

```text
gocloudlaunch.com/api/*
www.gocloudlaunch.com/api/*
```

## Local setup

```sh
cd cloudflare-worker
npm install
cp .dev.vars.example .dev.vars
```

Update `.dev.vars` with the real Lambda Function URLs and a long random `CLOUDLAUNCH_WORKER_SECRET`.

Run locally:

```sh
npm run dev
```

## Cloudflare secrets

Set these values in Cloudflare before deploying:

```sh
npx wrangler secret put DEPLOY_URL
npx wrangler secret put SECURE_GET_URL
npx wrangler secret put CREATE_USER_URL
npx wrangler secret put CLOUDLAUNCH_WORKER_SECRET
```

Use the same `CLOUDLAUNCH_WORKER_SECRET` value as an environment variable on the `Deploy`, `SecureGet`, and `CreateUser` AWS Lambdas.

## Deploy

```sh
cd cloudflare-worker
npm run deploy
```

## Frontend URLs

The frontend should use same-origin relative API paths:

```ts
export const DEPLOY_URL = "/api/deploy";
export const SECURE_GET_URL = "/api/secureget";
export const CREATE_USER_URL = "/api/createuser";
```

## Direct Lambda URL protection

Each Lambda now expects this request header:

```text
x-cloudlaunch-worker-secret: <CLOUDLAUNCH_WORKER_SECRET>
```

Requests missing the header, or using the wrong value, return `403`. This prevents callers from bypassing Cloudflare by using the raw Lambda Function URLs.
