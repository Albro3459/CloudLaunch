# React Frontend

This is the example CloudLaunch UI. It lets authenticated users interact with the AWS Lambda APIs for region setup, region cleanup, VPN deployment, VPN termination, and WireGuard config access.

The frontend uses React, TypeScript, Tailwind CSS, Firebase Authentication, and Firebase/Firestore data used by the example VPN implementation.

## Local Setup

Install dependencies:

```sh
cd react-frontend
npm install
```

Configure the frontend secrets from the examples in `src/Secrets/`:

* Firebase web app config
* Lambda endpoint URLs
* Source AWS region value

## Run Locally

```sh
cd react-frontend
npm start
```

The `start` script runs the React dev server and watches Tailwind output.

## Build

```sh
cd react-frontend
npm run build
```

## Deploy GitHub Page

The deploy command uses your local build output. It does not pull from any remote branch.

```sh
cd react-frontend
npm run deploy
```

This publishes the local `build/` folder to the `gh-pages` branch.
