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
search failures remain distinct.

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

