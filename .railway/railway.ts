import { defineRailway, project, service } from "railway/iac";

// platform-accounts-api: the Accounts cell. Variables stay unmanaged (secrets live in Railway only).
// accounts-api sleeps when idle (Railway Serverless) and wakes on the next request.
// Every service runs in Singapore next to Neon (aws-ap-southeast-1) and empire-platform; the IaC does not
// carry the region, so after the first deploy: railway scale --service <svc> asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0
// Every service deploys from GitHub main after CI passes (Railway Wait for CI, 2026-10-18).
// Declared here so `railway config apply` keeps the connection instead of removing it.
const github = {
  type: "github" as const,
  repo: "bookchaowalit/platform-accounts-api",
  branch: "main",
  checkSuites: true,
};

export default defineRailway(() => {
  const api = service("accounts-api", {
    source: github,
    healthcheck: "/health",
    healthcheckTimeout: 60,
    deploy: { sleepApplication: true },
  });

  // accounts-metadata-api: read-only account metadata API for solo-web (service-JWT auth, ACCOUNTS_API_AUTH_* variables).
  const metadata = service("accounts-metadata-api", {
    source: github,
    build: { builder: "DOCKERFILE", dockerfilePath: "services/accounts-metadata-api/Dockerfile" },
    healthcheck: "/ready",
    healthcheckTimeout: 30,
    deploy: { sleepApplication: true },
  });

  return project("platform-accounts-api", {
    variables: { managed: false },
    resources: [api, metadata],
  });
});
