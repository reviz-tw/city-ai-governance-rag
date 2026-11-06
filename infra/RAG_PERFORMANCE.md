# RAG latency and background preparation

Query answers default to `answer_detail: "progressive"`: show a quick take first,
then append the complete, normally reasoned answer automatically. Both bodies
are saved in one assistant message with one question and one citation namespace.
HTTP and MCP callers may explicitly request `brief` or `detailed` alone.

One retrieval authorizes and freezes the shared evidence snapshot. Full generation
starts in a bounded thread pool immediately while the preview streams. The full
answer uses the evidence independently, never the preview as grounding. Both model
calls stream: detailed fragments are buffered in a bounded queue during the preview,
then forwarded immediately after it, without waiting for full generation. The UI
shows a localized waiting status until the first detailed fragment arrives, then
smoothly reveals new text without replaying earlier fragments or moving the reader
away from the preview. Reduced-motion and show-answer controls bypass animation.
Each default answer has two model generations and one retrieval.

Preview generation uses `RAG_THINKING_LEVEL=LOW`, a short opening of up to two
sentences, and `RAG_BRIEF_MAX_OUTPUT_TOKENS=3072`. Its per-request HTTP read timeout
is `RAG_PREVIEW_TIMEOUT_MS=8000`. Full answers use
`RAG_DETAILED_THINKING_LEVEL=MEDIUM` and `GEMINI_MAX_OUTPUT_TOKENS=12000`, without the
preview length restriction. Extraction and artifact settings are unchanged.

Evidence now has a 24,000-byte budget (previously 9,000); the total prompt budget
is 36,000 bytes (previously 16,000). `CONTEXT_EVIDENCE_TOKENS` and
`CONTEXT_INPUT_TOKENS` retain their legacy names but count UTF-8 bytes, not model
tokens. Individual passages remain capped at 3,500 bytes and history at 3,000
bytes. Thus approximately seven maximum-sized passages can fit, or more shorter
passages, with further trimming if prompt/history overhead exhausts the total
budget. Retrieval counts and document diversification are unchanged. Empty usable
evidence returns a localized no-results response without answer generation;
search failures and pending-source preparation remain distinct.

Preview failure displays an incomplete-preview note but still permits a successful
full answer. Full failure retains the preview, received detailed text and citations, marks the turn failed,
and never reports preview-only output as completed. Hitting the output-token cap
also fails that generation. Disconnects preserve partial text as interrupted and
cancel queued full work. Running producers stop cooperatively and close their
stream after an in-flight read returns; blocked reads remain subject to provider
timeouts. The fragment queue holds at most 64 entries and cancellation unblocks a
producer waiting on a full queue. Four full-generation workers and eight admission
slots bound orphaned work. While
waiting, SSE heartbeat events keep the connection and conversation lease alive.
The foreground full-answer wait has the `GEMINI_TIMEOUT_MS` deadline.
Server traces record `detailed_model_first_text` and `detailed_first_text` (delivery
after the preview). Frontend `detailed_ready` records the first detailed fragment,
not the last. Streaming improves time to readable detail; it does not promise a
shorter total model generation time or eliminate the cost of expanded evidence.

Persisted follow-up rewrites return only `retrieval_query` and `city`, with a
512-token output cap; they retain the server's traceable summary and bounded
history. Explicit external non-persisted context retains the summary-capable
schema and 1024-token cap. Standalone questions still skip the rewrite when safe.

## Historical collection

The query path reads an authorized, prepared catalogue. It never downloads,
extracts or registers a missing historical source. Missing sources are counted;
answers with partial evidence show a warning. If all available historical matches
are unprepared, the request reports preparation pending, rather than claiming
that no evidence exists.

`city-legacy-catalog` is an isolated 1 CPU / 2 GiB Cloud Run Job. It scans only the
configured historical public bucket's `documents/` prefix. Source IDs are stable;
existing records, original bytes, reviewed drafts and published versions are never
overwritten. It commits files independently and uses a PostgreSQL advisory lock
against overlapping executions. Background extraction permits up to 2 million
characters for larger historical reports; interactive uploads retain their
500,000-character limit. New publications still follow the review/publish flow.

Cloud Build deploys and completes preparation before deploying a candidate.
An administrator bootstraps the hourly trigger once, separately from builds:

```sh
python3 infra/configure_legacy_catalog.py tdf-ocf asia-east1 \
  59297909591-compute@developer.gserviceaccount.com
```

The Scheduler trigger uses OAuth to invoke this private job at minute 15 each
hour (UTC). Its service account has `roles/run.invoker` on this job. Cloud Build
does not require project-wide Scheduler management permissions. Failed files are
reported with stable source IDs and exception types, without source text; the job
fails so that deployment/operations can catch incomplete preparation.

## Request timings

`/api/chat/stream` and `/api/rag/query` return `X-Request-ID`; source events also
include `request_id`. The browser writes JSON `rag_client_timing_ms` with sources,
first text, last text, stream completion and React-committed composer readiness,
including session creation and HTTP overhead. `post_text` measures the final text
fragment to the enabled composer, so persistence/summary tail latency is visible.
Logs contain no question, answer, source text, credential or account identifier.

Generation events carry `generation_phase` and use `brief_` / `detailed_` stage
prefixes. Browser timings also include `brief_complete` and `detailed_ready`.
Server events `rag_stage`, `rag_model_usage`, `rag_model_finish` and `rag_request`
correlate authentication, conversation begin/checkpoints/finish, context rewrite,
language resolution, managed catalogue permissions, remote search, result
verification, legacy lookup/passage matching, evidence construction, client setup,
model first text and full generation. Parallel stages overlap; do not add their
durations. Repeated stages each emit a log; the request summary records their most
recent duration. Handled SSE failures also mark the request failed.

## Reproducible model benchmark

Run the same backend image as a private Cloud Run Job with its runtime service
account. No database or private documents are required. Set `GCP_PROJECT_ID`,
`GEMINI_CHAT_MODEL`, `GEMINI_PROVIDER`, `GEMINI_LOCATION` and
`ARTIFACT_GCS_BUCKET`, then use:

```sh
python -m app.services.rag_benchmark --repeats 2 \
  --gcs-key benchmarks/rag-performance-UNIQUE_RUN_ID.json
```

Four fixed English, Traditional Chinese, Spanish and Japanese questions compare
three profiles: detailed/MEDIUM, brief/MEDIUM and brief/LOW. Profile order rotates
across questions and repeats. Evidence is synthetic and tests human review,
24-hour emergency exceptions, exclusion of budget decisions from the exception,
unmeasured representativeness and an unspecified budget. Review the full answers
for factual scope, citations and language; a numeric citation alone is not a
quality pass. Reports include raw answers, stop reasons, usage and per-run timings.
A short model-only benchmark does not establish end-to-end p95, cold-start latency
or a service SLA. Inspect correlated real-query traces separately.

## Cloud Run sizing

The web service remains at 1 CPU / 2 GiB, concurrency 4, min 0, max 2, with startup
CPU boost. Model inference and remote search run outside this container. More CPU
primarily helps local extraction and simultaneous CPU work; it cannot directly
speed remote model generation. More RAM provides memory headroom and avoids OOM,
rather than guaranteeing lower latency. For demos where idle cost is acceptable,
service-level minimum instances of 1 reduce scaling-from-zero delays. Benchmark
before raising CPU or concurrency; separate background work from the web service.

## Earlier verification: 2026-10-29 (brief-only default)

Released revision: `city-rag-backend-dev-b-2893ddc4-6cca-454b-826c-f5b1ec513943`.
Container checks: 195 backend tests, 31 frontend tests, TypeScript and Vite build.
Authenticated browser checks completed a brief answer, its detailed expansion,
then the city follow-ups “那台北呢？” and “那新北呢？”.

Same-question server pipeline observation (one fresh conversation per version):

| Measurement | Previous | Released |
| --- | ---: | ---: |
| First answer text | 9.237 s | 6.232 s |
| Pipeline complete | 13.021 s | 7.918 s |

That earlier browser run observed 6.735 s to first text and 8.456 s to an enabled
composer, including session creation and HTTP/rendering. Four browser requests
showed 0.303–0.728 s from the last text fragment to composer readiness. In the
fourth turn, durable finish/summary work took 60 ms; no summary model call ran.
Warm follow-ups spent about 1.0 s in rewriting and 2.4–2.6 s in retrieval. Managed
remote Search took about 2.2–2.4 s, versus 0.11–0.26 s verifying results and roughly
0.03–0.05 s selecting eligible publications. Further result-read batching is a
secondary optimization in these samples; permissions/version checks stay intact.

Final synthetic acceptance run (four runs per profile, successful requests only):

| Model-only profile | First text median | Complete median | Completed |
| --- | ---: | ---: | ---: |
| Detailed / MEDIUM | 6.244 s | 10.407 s | 4/4 |
| Brief / MEDIUM | 6.505 s | 7.625 s | 4/4 |
| Brief / LOW | 1.325 s | 2.618 s | 4/4 |

Earlier testing had one 120-second `ReadTimeout` in 24 calls. A subsequent
12-call check and final 12-call acceptance completed. Preserve the earlier failure;
these small samples cannot establish tail reliability, p95 or an SLA. The failure
occurred in a model-only job with no retrieval, so CPU sizing of the web service
cannot directly address that particular wait. An earlier brief prompt also made
overly broad opening claims; the released prompt starts comparisons with
separate per-city/task findings. The final brief answers were checked for scope,
unknown rules, citations, human-review exceptions and missing budget information.

All 22 historical sources are prepared. The hourly Scheduler invocation was
also exercised: all 22 records already existed and no file failed or was
rewritten. Machine sizing remains 1 CPU / 2 GiB, min 0, concurrency 4.

Raw synthetic answers, prior failures and correlated request observations are in
[benchmarks/rag-performance-2026-10-29.json](benchmarks/rag-performance-2026-10-29.json).

## Progressive-answer verification: 2026-10-29

Released revision: `city-rag-backend-dev-b-1205b08c-44fb-4dbe-adde-daeda9c108db`.
204 backend tests and 31 frontend tests passed, together with TypeScript/Vite and
deployment authentication checks. English and Traditional Chinese browser requests
showed the preview first, a waiting status, then the completed full answer without
an extra question or expand click. Reloading restored two questions and two
assistant messages, each containing both sections and their shared citations.

| Browser observation | English | Traditional Chinese |
| --- | ---: | ---: |
| First preview text, including retrieval | 5.800 s | 5.702 s |
| Preview complete | 6.904 s | 8.284 s |
| Full answer appended | 15.186 s | 26.403 s |
| Composer ready | 15.240 s | 26.447 s |

These are two live samples, not a latency SLA. The complete answer uses MEDIUM
reasoning and a normal output budget, so its latency depends on the requested
depth. The preview and full generation overlap, share one retrieval, and each
finished with `STOP`. Tests cover a failed preview, a failed full answer, queued
cancellation, bounded admission, full-ready-first ordering, persistence and SSE
heartbeats. Incomplete full answers retain the preview and fail the turn.

See [benchmarks/progressive-answers-2026-10-29.json](benchmarks/progressive-answers-2026-10-29.json)
for phase-specific timings and request IDs.
