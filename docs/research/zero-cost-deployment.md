# Zero-cost cloud deployment research

Date: 2026-10-16. Status: **proposed; no provider or broker change accepted**. Related PRD: R05, R17-R18, R20-R21. This note supports the [architecture proposal](rebuild-architecture.md) and [roadmap](../roadmap.md); it does not override the [PRD](../PRD.md).

## Evidence and present state

- **Owner-confirmed clarification:** Vercel frontend and DigitalOcean backend hosting were used on a different project, not Bangus Buhai. They are cost-experience context, not this project's deployment history. Bangus Buhai's actual frontend/backend hosting remains unverified; live services, account settings, usage and bills were not inspected.
- **Source-verified:** the [prototype backend](../../backend/main.py) combines API, MQTT lifecycle and inference, with [SQLite persistence](../../backend/database/db.py); see the dated [source map](../reference/architecture.md).
- **Source-verified:** the [rebuild backend](../../rebuild/backend/main.py) currently provides a health endpoint, the [frontend](../../rebuild/frontend/package.json) is React/Vite, and [device contracts](../../rebuild/contracts/README.md) are offline. These do not demonstrate a working cloud deployment. [Rebuild status](../status/rebuild.md) owns task progress.
- **Unverified:** Linux ARM dependency compatibility, inference memory/latency, farm load, cloud eligibility/capacity, live broker plan and production security/recovery. No account, application, hardware, build or deployment command was run for this research.

## Recommended candidate

Use Cloudflare Pages for the static frontend, plus one Oracle Always Free Ampere VM for separate API, MQTT-ingestion and job-worker processes and self-managed PostgreSQL. This preserves the proposed Python/React architecture and allows continuous device processing. It is a technical-fit recommendation, not a reliability guarantee.

| Part | Candidate | Evidence and limit |
|---|---|---|
| Website | Cloudflare Pages | [Static requests are free and unlimited](https://developers.cloudflare.com/pages/functions/pricing/); Functions have separate quotas. Build/file limits still apply. |
| Backend, database and CPU inference | Oracle Always Free A1 | Current [resource documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) lists 2 OCPUs/12 GB memory, 200 GB combined boot/block storage and 10 TB monthly outbound transfer. Capacity shortages and idle-instance reclamation apply. |
| Account | Oracle Free Tier | [Signup requires an eligible credit/debit card for verification](https://www.oracle.com/cloud/free/). Temporary trial credits are separate from ongoing free resources. |
| Backend hostname | Free DNS subdomain, e.g. DuckDNS | [DuckDNS provides free dynamic DNS](https://www.duckdns.org/about.jsp). The API still needs configured HTTPS and certificate renewal; the Pages hostname covers only the website. |
| MQTT | Unresolved | HiveMQ remains selected by the PRD. See the certificate conflict below. |

All proposed server roles share a failure point. We would own OS/container updates, database migrations, credential/certificate lifecycle, disk/log limits, monitoring and backup/restore. Use separate backup storage within its free allowance and test recovery. Keep PostgreSQL private. Train/evaluate models locally; qualify CPU inference on the chosen server. Do not assume a small model file means low runtime memory.

## Broker decision required before T07

The [HiveMQ plan comparison](https://docs.hivemq.com/hivemq-platform/connect/access-management-options-per-cloud-plan.html) says Serverless lacks X.509/mTLS. That conflicts with R17's device-certificate requirement. A successful password/TLS connection would not resolve it.

A candidate $0 alternative is self-hosted Mosquitto on the same VM, with individual device certificates and tested topic permissions. [Mosquitto supports required client certificates](https://mosquitto.org/man/mosquitto-conf-5.html). Certificate enrollment, renewal and revocation would become our responsibility.

Mosquitto was deliberately retired earlier. Reintroducing it would require an explicit broker decision and corresponding PRD R05/R18 and architecture updates before implementation. Nothing was restored or installed. Keeping HiveMQ plus the certificate requirement would instead require a compatible plan; account capabilities and cost remain to be checked. Do not silently weaken R17.

## Alternatives

| Service | Useful for | Why it is not the first choice for the complete system |
|---|---|---|
| [Render Free](https://render.com/docs/free) | Temporary API demonstrations | Sleeps after 15 minutes without inbound HTTP/WebSocket traffic; local files are ephemeral; free Postgres expires after 30 days. Render advises against production use. Outbound MQTT activity is not a dependable replacement for its documented wake/idle rules. |
| [Neon Free](https://neon.com/pricing) | Intermittent managed PostgreSQL | 1 GB and 100 CU-hours/month/project. Continuous telemetry may keep compute active and exceed the allowance; measure actual workload. It does not provide our persistent Python processes. |
| [Supabase Free](https://supabase.com/pricing) | Managed PostgreSQL/Auth experiments | 500 MB database, inactivity pausing and no automatic database backups. It does not host our existing FastAPI/PyTorch worker as a persistent Python service. |
| [Vercel Hobby](https://vercel.com/legal/terms) | Eligible personal/noncommercial frontend use | Terms restrict Hobby to personal/noncommercial use. Check eligibility for a real farm deployment. It does not solve continuous backend processing. |

## Guided deployment plan

1. Before accepting a host, verify account eligibility, actual free capacity, resource labels and Linux ARM/Python/PyTorch compatibility. Agree the broker/certificate decision before T07; do not wait until release.
2. Continue the existing build roadmap. T03 is the next available task; this research does not start it or mark future deployment tasks complete.
3. During T24, rehearse a containerized API/ingestion/worker deployment with private PostgreSQL, HTTPS/WSS, scoped credentials, migrations and separate test data. Configure the frontend to use the public API; never place secrets in its build.
4. During T26-T28, demonstrate backup restoration, restart/reconnect recovery, firmware buffering, authorization, measured load and documented rollout/rollback. Production readiness depends on this evidence.
5. Check provider terms and quotas again before provisioning. Use only ongoing free resources, no paid extras; include storage, logs, backups and transfer in the budget. Custom domains, SMS and other external services are separate costs unless independently covered.

If Oracle free capacity is unavailable, the managed alternatives above can support demos, but this research has not established an equivalent guaranteed $0 always-running production host. Keep deployment portable so infrastructure can change without rewriting product logic.
