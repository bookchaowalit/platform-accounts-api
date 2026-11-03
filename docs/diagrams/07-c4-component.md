# 07 — C4 Component (accounts-api)

```mermaid
C4Component
  title accounts-api - components
  Container_Boundary(api, "accounts-api") {
    Component(server, "cellkit.server.api", "uvicorn entry", "Reads env, builds verifier, cluster and platform client")
    Component(spec, "cellkit.spec", "Loader", "cell.yaml to Cell / Resource / Field")
    Component(app, "cellkit.app.create_app", "FastAPI", "Generic CRUD routes, correlation id, write path, error mapping")
    Component(auth, "cellkit.auth", "TokenVerifier + JwksKeys", "RS256, audience accounts-api, channel header")
    Component(plat, "cellkit.platform.HttpPlatform", "httpx", "decide, begin, finish, publish")
    Component(db, "cellkit.db", "psycopg", "LocalCluster / HostedCluster, migrate, provision")
    Component(risk, "solo_accounts.routes", "extend hook", "GET /v1/risk-report and analyse()")
    Component(sentry, "cellkit._sentry", "sentry-sdk", "init + scrub, capture()")
    Component(pub, "cellkit.publisher", "outbox sweep", "Inert here: no graph resources")
  }
  ContainerDb(neon, "Neon accounts DB")
  System_Ext(platform, "empire-platform")
  Rel(server, spec, "load cell.yaml")
  Rel(server, app, "create_app")
  Rel(app, auth, "verify bearer")
  Rel(app, plat, "authorize and record")
  Rel(app, db, "bound connection, set app.workspace_id")
  Rel(app, risk, "Context passed to register()")
  Rel(risk, db, "SELECT via ctx.bound")
  Rel(app, sentry, "capture on finish failure")
  Rel(db, neon, "SQL")
  Rel(plat, platform, "HTTPS")
```

Sources: `src/cellkit/server.py`, `src/cellkit/spec.py`, `src/cellkit/app.py`, `src/cellkit/auth.py`, `src/cellkit/platform.py`, `src/cellkit/db.py`, `src/cellkit/_sentry.py`, `src/cellkit/publisher.py`, `src/solo_accounts/routes.py`, `src/cellkit/__init__.py`, `docs/cellkit-notes.md`

หมายเหตุ: `cellkit` เป็น code ของ repo นี้เอง (ADR-0001) ส่วน `cellkit.mcp`, `cellkit.importer`, `cellkit.contract`, `cellkit.testing` ไม่ได้อยู่ใน runtime path ของ API

## Open questions
- ไม่มี
