# RAG latency and background preparation

Query answers default to `answer_detail: "progressive"`: show a quick take first,
then append the complete, normally reasoned answer automatically. Both bodies
are saved in one assistant message with one question and one citation namespace.
HTTP and MCP callers may explicitly request `brief` or `detailed` alone.

One retrieval authorizes and freezes the shared evidence snapshot. Full generation
starts in a bounded thread pool immediately while the preview streams. The full
answer uses the evidence independently, never the preview as grounding, and is
appended only when fully generated. The UI shows a localized waiting status after
the preview; it no longer asks users to click More detail or repeat the question.
Each default answer has two model generations and one retrieval.

Preview generation uses `RAG_THINKING_LEVEL=LOW`, a short opening of up to two
sentences, and `RAG_BRIEF_MAX_OUTPUT_TOKENS=3072`. Its per-request HTTP read timeout
is `RAG_PREVIEW_TIMEOUT_MS=8000`. Full answers use
`RAG_DETAILED_THINKING_LEVEL=MEDIUM` and `GEMINI_MAX_OUTPUT_TOKENS=12000`, without the
preview length restriction. Extraction and artifact settings are unchanged.

Preview failure displays an incomplete-preview note but still permits a successful
full answer. Full failure retains the preview and citations, marks the turn failed,
and never reports preview-only output as completed. Hitting the output-token cap
also fails that generation. Disconnects preserve partial text as interrupted and
cancel queued full work. Already running calls finish under provider timeouts;
four full-generation workers and eight admission slots bound orphaned work. While
waiting, SSE heartbeat events keep the connection and conversation lease alive.
The foreground full-answer wait has the `GEMINI_TIMEOUT_MS` deadline.

