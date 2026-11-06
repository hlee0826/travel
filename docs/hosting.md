# Vercel + Supabase test hosting

Deployed November 6, 2026: **https://minhwa.pinnedby.com**.
The existing pinnedby.com deployment and data remain separate. Minhwa has its own
Vercel project, restricted cloud database login, and private storage buckets.
Password login, authenticated pages, signed resumable uploads, sample checkout,
and anonymous access protection are verified live. A real hosted portrait completed
photo review, generation with all five input hashes, all nine artwork checks, and
artifact rendering. PNG/JPEG downloads and blocked public storage URLs also passed. Checkout and fulfillment are simulated.

## Architecture

- FastAPI on Vercel serves the unchanged website behind a shared password. Every
  application route and asset requires a secure, HTTP-only session cookie.
- Supabase PostgreSQL holds sessions, uploads, jobs, attempts, stage checkpoints,
  budget reservations, and test orders in the isolated `minhwa` schema.
- Browser photos upload directly to the private `minhwa-uploads` bucket using
  scoped signed TUS uploads. Large images never travel through Vercel's request body.
- The Python Vercel Workflow SDK triggers photo check → painting → quality check
  → immutable download rendering. Each step fits within a function invocation;
  the workflow persists between invocations. There is no always-on worker.
- Supabase pg_net wakes the dispatcher after a committed attempt. A one-minute
  Supabase cron checks for undispatched/stalled attempts; it only makes an HTTP
  request when work is due. The SDK handles normal workflow continuation.
- Original photo plus all four private painting references are used. Identity,
  fresh painting, garden interaction, and all nine existing quality checks remain.
- Every paid call gets a database claim first. Re-delivery returns saved results;
  interrupted/ambiguous calls stop for operator reconciliation rather than paying
  again. A successful OpenAI response lost before persistence cannot be recovered
  automatically; inspect provider usage before allowing another attempt.
- Previews and masters live in private `minhwa-artwork`. Owner-checked routes issue
  two-minute signed links. A copied signed link remains usable until it expires.
- The $300 rolling 24-hour allowance reserves $3 per attempt, including failures.
  **This is an admission allowance, not a guaranteed OpenAI billing cap.** Keep
  provider billing controls in place. Six attempts/session/day; three/photo/day;
  three/job and at most two accepted paintings.

## Local verification

Keep the existing `server.py` local app and `.studio` collection as-is. Hosted data
starts separately; no automatic import of private local uploads/orders.

```
uv sync --locked
npm ci
npm run build:upload
.venv/bin/python deploy/prepare_vercel.py
.venv/bin/python -m unittest discover -s tests -q
```

The hosted database tests additionally require a **disposable** local PostgreSQL
instance and `MINHWA_TEST_DATABASE_URL`. The suite intentionally refuses remote
URLs because it truncates Minhwa test tables. Use port 55487 and local user stevenlee,
or explicitly adapt that safety guard for your own disposable instance.

## Provision and deployment sequence

1. Use a separate Vercel project, `minhwa`, in the intended account. Preserve the
   existing Pinned project. Confirm plan eligibility before publishing this
   commercial product; no subscription change is performed by these scripts.
2. Supply the existing Supabase admin connection privately as
   `MINHWA_ADMIN_DATABASE_URL`, a generated password as `MINHWA_DATABASE_PASSWORD`,
   and `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`. Run
   `.venv/bin/python deploy/provision_supabase.py`. It creates only Minhwa objects
   and a `minhwa_app` database login. It refuses to replace an existing login.
   Do not expose the `minhwa` schema through the Data API. The restrictive Minhwa storage policy blocks anon/authenticated access to both
   buckets, including when the shared project has broader permissive policies.
   Signed uploads/downloads remain scoped capabilities; verify them live.
3. Use Supabase's transaction-pooler URL with the **minhwa_app** login, SSL required,
   and its generated password as `MINHWA_DATABASE_URL`. Prepared statements are
   disabled. Runtime credentials must not be the existing Pinned/admin DB login.
4. `.venv/bin/python deploy/configure_hosted.py` privately prompts for credentials
   and writes `.env.hosted.local` mode 0600. It stores only a salted scrypt hash of
   the shared studio password. Save that password in your password manager.
5. Add the individual settings in that file as **sensitive production-only** Vercel
   environment variables. Do not upload the file. Keep preview credentials separate;
   generation is disabled for `VERCEL_ENV=preview`. Enable Vercel system environment
   variables for Workflow OIDC; keep `WORKFLOW_PUBLIC_MANIFEST` unset.
6. Build the upload bundle and run `deploy/package_vercel.py` before every deployment.
   Extract `dist/minhwa-vercel-source.tar.gz` into a clean release directory, copy
   only `.vercel/project.json` for project linking, and deploy that directory.
   The archive has an explicit runtime allowlist: no `.env*`, `.studio`, local photos, operator
   exports, research files, tests, Render configuration, or `public/` directory.
   `hosted_web/` is served only through FastAPI. **Do not deploy public/ as static
   assets: that would bypass the password gate.** Inspect the Vercel build output
   for the generated Workflow endpoints and authenticated asset routing. Do not
   copy the workspace `.vercelignore` over the archive's generated version:
   Vercel's wildcard negation handling previously omitted nested application files.
7. Set the custom domain `minhwa.pinnedby.com` on this project, then add only its
   subdomain DNS record using the exact target Vercel supplies. Do not change apex,
   www, nameservers, or another deployment's settings. Wait for HTTPS.
8. Store `minhwa_origin` and `minhwa_dispatch_secret` in Supabase Vault with the
   exact production origin and dispatcher secret. Apply `supabase/dispatch.sql`
   from the admin connection. Never embed a secret in SQL source or cron text.
9. With generation still disabled, verify password, CSRF, ownership, secret-path
   blocking, private buckets, demo checkout, downloads, and mobile layout on the
   actual domain. Then enable generation and test one consented photo end-to-end,
   closing the tab and reopening it to verify server-side continuation.

The Python Workflow SDK is beta. Hosted queue authentication, step duration,
recovery, and package size must be confirmed on a real deployment before enabling
paid calls. On Hobby, individual calls may time out; the hosted setting uses a
240-second OpenAI timeout to leave room for persistence inside a 300-second
function. Slow calls become an operator check, never an automatic paid retry.

## Operator review and recovery

Load the private server settings in a trusted shell without printing them.

```
.venv/bin/python -m hosted.admin list
.venv/bin/python -m hosted.admin inspect --job JOB_ID --directory /private/tmp/minhwa-review-unique
.venv/bin/python -m hosted.admin approve --job JOB_ID --note "Compared original and all nine criteria; explain the manual override."
.venv/bin/python -m hosted.admin reject --job JOB_ID --note "Explain the failed likeness or composition check."
.venv/bin/python -m hosted.admin reconcile --job JOB_ID --note "Checked provider usage and request outcome; explain why a new attempt is safe."
```

Approval intentionally overrides a failed automatic check; inspect both images
and `review.json` first. Rendering must succeed before approval becomes visible.
Review files contain private photos: delete them after use. Customers cannot access
these commands through the shared site password.

A login session lasts seven days. Signing out or rotating the password/session
secret invalidates access to that session's collection; this test build has no
customer account recovery. Database records are retained. Preview is not a payment
or print fulfillment system.

## Rollback

Set `MINHWA_GENERATION_ENABLED=false` and redeploy to stop new admissions. Already
running provider calls may finish; inspect active attempts before changing secrets
or schemas. Disable only `minhwa-dispatch-recovery` and the Minhwa insert trigger
if stopping recovery. Keep private buckets and database records for investigation.
The existing local app and pinnedby.com remain available. Render files are retained
as an unused alternative and excluded from the Vercel deployment.

References: [Vercel Python workflows](https://vercel.com/kb/guide/python-and-durable-workflows),
[Supabase resumable uploads](https://supabase.com/docs/guides/storage/uploads/resumable-uploads).

## Verification completed locally

November 6: 37 application/hosting tests and 3 reference-workflow tests passed.
These cover the original local app, password/origin checks, owner-only access,
concurrent budget admission, idempotent submissions/retries, interrupted-call
handling, all five image inputs, nine quality gates, immutable rendered files,
and restrictive shared-project storage policies. Paid calls and Storage transport
were mocked; SQL ran against real disposable PostgreSQL.

Chrome over local HTTPS passed login, sample creation, explicit approval, test
checkout, and PNG download. The build's dependency lock and browser JavaScript
syntax were checked. The runtime source archive was checked to exclude private
files and the locally configured API key.

Vercel CLI 64.5 successfully started the app, Workflow sidecar, and local queue.
The app correctly returned 503 without its required production configuration.
The local production-build attempt hit a Vercel cross-platform limitation: Linux
Pydantic binaries cannot be introspected with macOS Python. Do not deploy a
Mac-native prebuilt bundle; use a source deployment built on Vercel Linux.

Still pending: Linux production build, actual Supabase provisioning and TUS
upload, hosted Workflow delivery/recovery, DNS/TLS, and one live paid generation.
No live Supabase records, DNS, subscriptions, or API billing were changed by this
implementation session.
