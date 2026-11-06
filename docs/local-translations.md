# Persistent local chunk translations

Published chunks are translated into `zh-TW`, `en`, `ja`, `fr`, `es`, and `ru` by a
separate local worker. Same-language output uses the original text. Additional
supported languages (`zh-CN`, `ko`, `de`) are queued on demand.

This is an additive database change (`chunk_translations`). Web startup creates
its table through the existing `store.initialize()` schema initialization. The
publication transaction queues all six languages after index verification. It
never runs a model or waits for translation. Existing publications need the
backfill command below. Do **not** deploy this change with the web-only image:
both backend and frontend must be deployed together.

The source reader now pairs the **published chunk text** with its translation,
including the original block/page references. Legacy block citations map to the
published chunks that contain those blocks. Stale versions are rejected, and
unpublished documents remain readable but cannot yet use this translation path.
Translations are not indexed, are not individual users' expiring artifacts, and
are only returned after checking the source document's current access rights.

## GCP deployment selected for this project

The production configuration selects Google's **TranslateGemma 12B**, distributed
by the official Ollama library, with manifest
`sha256:c2f9a9ca1ec7149f2422581c89937ab0363d9399d9355514d753ee012e99c252`.
No alternative model or Gemini API fallback is used for chunk translation.
This identifies the selected model supplier; it is not a certification of every
dependency in the existing application.

`backend/translation_worker/Dockerfile` bakes the model into a separate image.
Both upstream runtime images are digest-pinned in
`infra/cloudbuild.translation.yaml`. Build and startup verify the model manifest.
Ollama listens only on loopback, has cloud features disabled, and is called with
deterministic decoding. The application preserves source layout and URLs.

The GPU job runs in `asia-southeast1` using one NVIDIA L4, 4 vCPUs and 16 GiB RAM,
and connects to the existing Taiwan Cloud SQL instance with the existing runtime
service account. It has one task, no automatic whole-job retries, and a hard
timeout of 15 minutes. The worker stops between chunks after 12 minutes; rerunning the same job
continues the persistent queue without translating completed rows again. Production
sets `TRANSLATION_MAX_ATTEMPTS=1`: errors are logged and persisted as failed, with
no automatic retry. Only an explicit `--retry-failed` resets failed rows. There is
no automatic scheduler or unbounded execution loop.
If the shared model service becomes unavailable, the worker records the affected
row and stops the execution immediately with a nonzero exit code. Content validation
failures and the specific Ollama token-repeat-limit error remain isolated to the
individual row. Unknown HTTP errors still halt the batch. Ollama runtime errors are sent to Cloud Logging;
request-body debug logging is explicitly disabled.

Run these commands from the repository root in an authenticated Cloud Shell:

```bash
gcloud builds submit --project=tdf-ocf --config=infra/cloudbuild.translation.yaml --substitutions=_TAG=translation-YYYYMMDDa
python3 infra/deploy_translation.py queue --tag translation-YYYYMMDDa
python3 infra/deploy_translation.py job --tag translation-YYYYMMDDa
python3 infra/deploy_translation.py sample --tag translation-YYYYMMDDa
# Inspect the execution logs and translations before starting the full queue.
python3 infra/deploy_translation.py web --tag translation-YYYYMMDDa
python3 infra/deploy_translation.py backfill --tag translation-YYYYMMDDa
python3 infra/deploy_translation.py status --tag translation-YYYYMMDDa
```

The web deployment retains existing service settings/IAM, checks the candidate,
and only then promotes that exact revision. Deployment scripts do not add IAM
bindings or silently choose another model/region if the GPU quota is unavailable.
The build itself does not deploy or execute GPU inference. Executions are explicit;
without an active execution or separately configured trigger, new work stays queued.
Queue preparation and status inspection run in a separate CPU-only job in Taiwan,
with a five-minute timeout and no task retries; they do not allocate a GPU.
Run `queue` before inference. GPU executions consume the prepared queue without
re-scanning every publication; `backfill` in the deployment helper means consuming
that queue, while the native worker's `--backfill` flag creates missing rows.

Budget controls are independent: Cloud Run enforces `timeoutSeconds=900` and
`maxRetries=0`; the worker uses `--max-seconds 720` and
`TRANSLATION_MAX_ATTEMPTS=1`. The GPU launch helper refuses a second execution
while an earlier GPU execution is active. Task parallelism alone does not prevent
multiple independently started executions. Do not wrap the helper in an
unbounded loop or configure a Scheduler retry policy.

For this project the requested non-redundant L4 capacity is one GPU in
`asia-southeast1`, under quota preference `city-translation-l4-singapore`.
Check its granted value before expecting a GPU deployment to run:

```bash
gcloud beta quotas preferences describe city-translation-l4-singapore --project=tdf-ocf --format='yaml(quotaConfig,reconciling)'
```

## Optional native Transformers runtime

Use Python 3.12. The model dependencies are deliberately excluded from the Cloud
Run web container. Run from the repository root:

```bash
python3.12 -m venv .venv-translation
.venv-translation/bin/pip install -r backend/requirements.txt -r backend/requirements.translation.txt
```

Download/access the chosen Google model using your own Hugging Face account if
the repository requires it. The operator must accept its applicable model terms;
the application does not automate that step. The first model load downloads
weights; subsequent runs can use `--local-files-only`.

The adapter uses TranslateGemma's official processor chat template and measures
its actual token count. The default is 4B **as a provisional baseline**, not a
claim of validated policy-document translation quality. The same adapter supports
12B/27B with an explicit model setting, subject to available memory. Other model
families require their own adapter; changing the model name alone is insufficient.

The following values must agree between the deployed service and local worker:

```bash
export TRANSLATION_MODEL=google/translategemma-4b-it
export TRANSLATION_MODEL_REVISION=main
export TRANSLATION_RULES_VERSION=chunk-translation-v1
```

Before a production quality benchmark, pin `TRANSLATION_MODEL_REVISION` to the
chosen model repository's immutable commit SHA **on both service and worker**.
`main` is only the bootstrap default. A revision/rules/model change produces a new
cache identity; it does not silently serve a different model's previous output.
Weights, tokenizer and processor must come from that same revision.

For a local database, supply `DATABASE_URL` through the environment; never put a
production URL/password in this document, shell history or command arguments.

```bash
PYTHONPATH=backend .venv-translation/bin/python -m app.translation_worker --backfill --queue-only
PYTHONPATH=backend .venv-translation/bin/python -m app.translation_worker --device auto
PYTHONPATH=backend .venv-translation/bin/python -m app.translation_worker --status
```

`auto` selects CUDA, Apple MPS, then CPU. The native Transformers adapter uses
full model weights (no quantization): allow for weights **plus** model/runtime
memory, not just parameter-count estimates. Validate on the actual machine.

## Backfill the existing deployed data

This repository already uses Cloud SQL Proxy and the signed-in operator's gcloud
credentials in `backend/scripts/cloud_database.py`. The worker uses that same
path with `--cloud-db`; it does not create browser sessions or new credentials.
First have an authenticated Cloud SQL Proxy listening on `127.0.0.1:54329` for
`tdf-ocf:asia-east1:city-governance-postgres`. For example, using existing IAM access:

```bash
cloud-sql-proxy --address 127.0.0.1 --port 54329 tdf-ocf:asia-east1:city-governance-postgres
```

The proxy and `gcloud` must both have working existing credentials. Then:

```bash
# Add the table if needed and queue missing current-version chunks. Safe to repeat.
PYTHONPATH=backend .venv-translation/bin/python -m app.translation_worker --cloud-db --backfill --queue-only
# First inspect a small sample before running the whole corpus.
PYTHONPATH=backend .venv-translation/bin/python -m app.translation_worker --cloud-db --document DOCUMENT_ID --limit 10
# Drain the queue, including bounded retries. No Gemini fallback.
PYTHONPATH=backend .venv-translation/bin/python -m app.translation_worker --cloud-db
# Observe completed / queued / running / failed / blocked counts for current versions.
PYTHONPATH=backend .venv-translation/bin/python -m app.translation_worker --cloud-db --status
```

Use `--watch` to stay available for future publications. Closing the worker does
not affect reading already stored translations. Without a running worker, new
translations remain visibly queued. `--limit` bounds attempts, not successful
translations; failed jobs can consume an attempt. `--document` limits all work to
one document. `--retry-failed --queue-only` explicitly resets exhausted jobs after
an operator resolves the issue. Routine reader polling never resets retries.

## Persistence, retries and validation

- Identity includes document, published version, chunk ID, source text hash,
  source/target language, model, model revision and translation rules version.
- Unchanged completed text can be reused within the same document across versions.
  Changed source content is queued again. Old versions are never returned for a
  current citation, and only current versions are selected by the worker.
- A lease token prevents a crashed/slow worker from overwriting a replacement
  worker's result. A heartbeat runs during long local inference. Interrupted work
  is reclaimed; each chunk/language gets at most three attempts by default.
- On retry, smaller source segments reduce truncation risk. URLs, tabs and newline
  boundaries are preserved by application code rather than regenerated as JSON.
- Numeric comparisons normalize common grouping/decimal notation and explicit
  magnitude units. Ambiguous/unrecognized formats can still fail validation.
- OCR-blocked source chunks are blocked separately. A failure does not block other
  chunks or languages. Failure codes are visible in the reader and worker logs;
  source text and model output are not logged.
- Mechanical checks do **not** establish semantic completeness, correct negation,
  terminology or policy accuracy. Benchmark the chosen model/quantization on
  representative passages (including the previously failing documents) and have
  language-competent reviewers inspect the outputs before declaring quality ready.

## API and compatibility

`POST /api/library/{document_id}/translations` reads cached results and queues
missing requested translations. Body: `language`, optional `version`, `chunk_ids`
or legacy `block_ids`, and optional `original_hash` for legacy source citations.
An empty selection means the full published document. The response contains
`version`, `complete` and independent original/translated `chunks` with status,
error code and source references.

`GET` on the same endpoint polls without queueing. Use repeated `chunk_ids` or
`block_ids` query arguments. Both paths enforce document permissions and reject
stale versions. The source reader polls only while work is queued/running.

The MCP `translate_governance_document` tool returns the same persistent result;
repeat it to check progress. It no longer returns an artifact job ID. New legacy
`POST /api/artifacts` translation requests return 410. Old artifact results remain
readable until their existing expiry, but their retry action redirects users to
the new reader instead of issuing another Gemini request.

## Verification

### 2026-11-04 deployment and capped trial

- Web revision `city-rag-backend-dev-translation-20261104b` serves 100% of
  traffic on the existing URL after health, authentication, and Admin checks.
- CPU preparation found 234 published documents / 23,681 chunks and created
  142,086 language records. 23,681 records reuse the source language; these are
  **not new model-generated translations**. 130 records are blocked by OCR.
- The initial GPU execution `city-translategemma-j7djj` ran from
  `2026-11-04T13:13:11Z` to `13:15:31Z`, with zero task retries. All 12 attempted
  translations failed with HTTP 500 because the packaged runner was in
  `/usr/lib/ollama`, while `/usr/local/bin/ollama` searched `/usr/local/lib/ollama`.
  No successful corpus translation was generated. Remaining queue: 118,263;
  failed: 12. Failed rows were not reset.
- The corrected runner path was verified in a CPU-only diagnostic, using a
  synthetic English sentence translated to French. HTTP 200, complete output,
  and the year 2026 were verified. This is not a six-language quality benchmark
  or a GPU throughput measurement, so it cannot support a full-corpus cost estimate.
- The user selected a 15-minute total trial cap. No further GPU execution was
  started during that initial trial, and no automatic scheduler was created.
  The runtime correction is packaged separately
  by `infra/cloudbuild.translation.patch.yaml`; updating a job does not execute it.
- The runtime patch build `d42019db-6fa2-4da7-bd7a-678364d0bdc9` succeeded.
  Job `city-translategemma` now uses the immutable image digest
  `sha256:7e8d3b8538acf793bf97ad2887faeb2eb1383a629c5f1cac59b221b3c5c8c87c`
  (tag `translation-20261104c`). The deployed configuration was verified:
  one task, parallelism one, 900-second task timeout, zero task retries,
  `--max-seconds 720`, and `TRANSLATION_MAX_ATTEMPTS=1`.
  Model-service failures now stop the worker after logging the failure.

### 2026-11-04 corrected GPU trial (separately authorized)

- The user authorized one additional test capped at 15 minutes. Execution
  `city-translategemma-cb72q` used the patched image above and one NVIDIA L4.
  Logs confirmed all 49 model layers were offloaded to the GPU.
- Start: `2026-11-04T13:45:00.614075Z`; completion:
  `2026-11-04T13:57:46.343886Z` (12 minutes 45.73 seconds). The worker ended
  normally with its 720-second between-chunk limit; Cloud Run retained its
  900-second hard timeout. One task succeeded, zero tasks retried, zero running
  tasks at final verification. No additional execution was started.
- Processed 132 chunk/language records: **79 new translations accepted and
  persisted**, 53 rejected, for a mechanical acceptance rate of 59.8%.
  All 53 failures were `numbers_mismatch`; failures were logged without retries.
  This check alone cannot distinguish formatting differences from missing or
  altered numbers; failed outputs were not published as usable translations.
- Final database counts reported by the worker: completed 23,760 (23,681
  original-language copies plus 79 new translations), failed 65 (12 previous
  failures plus 53 new), queued 118,131, OCR-blocked 130. No running rows were
  reported in the final statistics.
- Including startup, observed throughput was about 10.3 attempted records/minute
  and 6.2 accepted translations/minute. This sequential queue sample is not a
  representative six-language semantic-quality benchmark or a full-corpus cost
  estimate. Investigate numeric mismatches before launching a full backfill.

The source reader displays queued/failed/blocked states. New publications enqueue
translations, but inference requires an explicit bounded worker execution. Do not
claim the existing corpus is fully translated or that the worker is always running.

### 2026-11-04 English-only trial and numeric validation repair

- English trial `city-translategemma-9pxhk` ran from
  `2026-11-04T14:13:34.949921Z` to `14:26:25.877505Z`, within its
  900-second timeout, with no retries. It attempted 165 records: 134 accepted,
  31 rejected with `numbers_mismatch`. English counts changed from completed
  527 / failed 14 / queued 23,114 to completed 661 / failed 45 / queued 22,949;
  26 OCR-blocked records remained blocked. Completed totals include source copies.
- An explicit diagnostic limit saved the 31 failed **segments** in the private
  `translation_diagnostics` table. These are neither full chunk translations nor
  published API results. Logs contain IDs and failure codes, not source passages.
- Numeric normalization now handles Chinese/formal list numbering, narrowly
  identified ROC years, named-month dates and AM/PM clocks, Chinese magnitude
  quantities and shared-unit ranges. Replaying the saved candidates resolves
  24 of the 31 rejections. Seven remain rejected: these include omitted 1999
  identifiers, a tenfold budget error, an incorrect year, and unsupported mixed
  prose/number formats. This is not a claim that all numeric formats are covered.
- The prompt explicitly preserves numbers and service identifiers. Normalization
  does not remove the numeric check or establish semantic translation accuracy.
- Translation, Ollama, and publication regression suites: 75 passed.
- English workers scope claiming, stale lease recovery, status, and explicit
  failure reset to English. No automatic reset of failed records is enabled.
- Deployment uses `infra/translation_overlay.py` on the immutable model image
  above, with SHA-256-checked source payload
  `e624332d3072628563402ce275a34cbbf934666a2646188d9fe9a452e756ad72`.
  The finite batch configuration is 180 tasks, parallelism 1, 900 seconds/task,
  zero task retries, worker 720 seconds, `TRANSLATION_MAX_ATTEMPTS=1`.
  At the checked Singapore list rate of US$1.255824/hour (L4 + 4 CPU + 16 GiB),
  its 45 task-hours correspond to approximately US$56.51 compute. This does not
  cap the entire GCP bill, taxes, storage, or other existing services.
- A model inference outage marks the execution halted in `translation_batches`;
  subsequent tasks exit before inference. Queue exhaustion also skips model
  loading. No recurring scheduler is installed.
- The operator explicitly reset exactly 45 current English failures once after
  the repair, resulting in 22,994 queued English records. Other languages were
  not reset. Execution `city-translategemma-8rhrb` was then started with the
  finite configuration above. Completion of the corpus remains pending; failed
  or OCR-blocked records are not guaranteed to become successful translations.
- Execution started at `2026-11-04T14:38:51.860539Z`. At
  `14:41:45.370319Z`, the repaired worker had attempted nine priority English
  repairs: four accepted, five rejected. Counts were completed 665 / failed 5 /
  queued 22,985 / OCR-blocked 26. Cloud Run reported one running task, zero
  failed tasks and zero retried tasks. These first priority repairs are a biased
  sample and must not be treated as the full-corpus acceptance rate.

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_translations.py backend/tests/test_publication.py backend/tests/test_workspace.py -q
cd web
npm test
npm run build
```

Tests use a fake model to verify orchestration without API charges or downloading
weights. Passing these tests is not a model quality or hardware benchmark.

### 2026-11-05 HTTP 500 investigation and repair

- The earlier finite execution `city-translategemma-8rhrb` stopped inference at
  `2026-11-04T14:58:48Z` after one HTTP 500. Later tasks skipped the halted batch
  but returned exit code 0, so 180 successful tasks did **not** mean corpus
  completion. Final English counts were 859 completed, 83 failed, 22,713 queued,
  and 26 OCR-blocked. Completed totals include 512 original-English copies.
- Diagnostic execution `city-translategemma-hxww2` explicitly retried only
  translation `19e232fc3173d6fa0d8b02f30a17739623ab742909f694f27bd31860cda507ca`
  once. The same table-of-contents line reproduced HTTP 500 with JSON error
  `prediction aborted, token repeat limit reached`. The runner remained available;
  this was an inference repetition abort, not an observed GPU crash or outage.
- Long dot leaders are now preserved in application code alongside newlines,
  tabs and URLs. The model translates the surrounding prose. Numeric and other
  output validators remain unchanged. Only the exact observed HTTP 500 error
  becomes `model_repetition`; that row fails without automatic retry and the
  worker proceeds to the next row. Other HTTP/network failures still halt.
- HTTP failures retain a bounded response excerpt and failing source segment in
  the private diagnostic table when diagnostics are enabled. Logs include only
  identifiers, HTTP status and a response hash. Failed/stopped executions now
  exit nonzero, and model initialization failures also mark the batch halted.
- The repair source payload SHA-256 is
  `b2a6829d0efc5b03a09ba5944edea5f88dd2cbf4cbc67147f33ffa83091c35b6`.
  Translation, Ollama and publication suites passed 89 tests.
- Corrected validation execution `city-translategemma-5p6cv` started at
  `2026-11-05T12:02:33.154816Z`, with one task, 900-second hard timeout, zero
  task retries and one attempt per row. The original failing c147 row completed
  and persisted its English translation, retaining table number 6 and page 65.
  At the first post-fix database check, English completed had increased from
  859 to 910; failed was 87, queued 22,657 and running 1.
- A one-shot Cloud Shell continuation waits at most 900 seconds for this exact
  validation execution to complete successfully with no task retries. It also
  requires the original failing row to be completed and the source digest to
  remain unchanged before calling the existing no-overlap deployment helper.
  Its continuation is 170 sequential tasks, 900 seconds per task,
  zero retries: at most 42.5 task-hours / US$53.37 list compute. Conservatively
  counting elapsed time of prior runs plus both new tests gives approximately
  US$57.58 combined compute. This is an estimate, not a billing-account cap.
  No recurring scheduler or automatic requeue of failed records is configured.
- Validation task 0 ran from `2026-11-05T12:02:42Z` to `12:15:35Z`, exited 0,
  with zero task retries. It accepted 134 translations and rejected 28; the
  final logged English counts at `12:15:29.298825Z` were completed 993, failed
  110, queued 22,552 and blocked 26, with no running row. The original failing
  row passed. The one-shot gate then launched `city-translategemma-84f72`, whose
  execution start time was `2026-11-05T12:16:17.364818Z`;
  Cloud Run showed one running task out of 170, zero failed tasks and zero
  retries. The continuation retained the exact validated source digest.
- At the first continuation database check, English counts were completed 993,
  failed 110, queued 22,551, running 1 and OCR-blocked 26. This is still an
  incomplete corpus; failed and blocked rows are not counted as successful
  translations. The Cloud Shell continuation process exited after its single
  launch, leaving execution and time limits enforced by Cloud Run.
