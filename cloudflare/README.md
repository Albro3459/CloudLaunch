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
cd cloudflare
npm install
cp .dev.vars.example .dev.vars
```

Update `.dev.vars` with the real Lambda Function URLs and a long random `CLOUDLAUNCH_WORKER_SECRET`.

`.dev.vars` **MUST** go in the same directory as [wrangler.toml](./wrangler.toml)

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

Use the same `CLOUDLAUNCH_WORKER_SECRET` value in the `cloudflare` block of the `CloudLaunch` AWS Secrets Manager payload used by the `Deploy`, `SecureGet`, and `CreateUser` AWS Lambdas.

## Publish

```sh
cd cloudflare
npm run publish
```

## Frontend API origin

The frontend uses same-origin relative API paths in production:

```ts
/api/deploy
/api/secureget
/api/createuser
```

For local React development, run `npm run dev` in this folder, then run `npm start` in `react-frontend`. The React start script sets `REACT_APP_API_ORIGIN=http://localhost:8787`, so browser API calls go to the local Worker instead of the CRA dev server.

## Direct Lambda URL protection

Each Lambda now expects this request header:

```text
x-cloudlaunch-worker-secret: <CLOUDLAUNCH_WORKER_SECRET>
```

Requests missing the header, or using the wrong value, return `403`. This prevents callers from bypassing Cloudflare by using the raw Lambda Function URLs.
