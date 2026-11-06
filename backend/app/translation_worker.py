"""Local model worker and resumable backfill: python -m app.translation_worker --help."""
import argparse
import json
import logging
import os
import threading
import time
from app.core.config import settings
from app.services import store, translations
from app.services.languages import LANG_NAMES

logger = logging.getLogger(__name__)


class ModelUnavailable(RuntimeError):
    """Stop this execution when the shared model service cannot run inference."""


def batch_halted(execution, halt=False):
    if not execution:
        return False
    with store.session() as db:
        batch = db.get(store.TranslationBatch, execution)
        if halt:
            if batch is None:
                batch = store.TranslationBatch(id=execution)
                db.add(batch)
            batch.halted, batch.reason = True, 'model_unavailable'
            db.commit()
        return bool(batch and batch.halted)


def process_one(translator, document_id=None, language=None, diagnostic_budget=None):
    claimed = translations.claim(document_id, language)
    if not claimed:
        return False
    row, chunk = claimed
    stop = threading.Event()
    lost = threading.Event()
    def renew():
        while not stop.wait(settings.TRANSLATION_LEASE_SECONDS/3):
            try:
                if not translations.heartbeat(row):
                    lost.set()
                    return
            except Exception:
                lost.set()
                return
    thread = threading.Thread(target=renew, daemon=True)
    thread.start()
    try:
        text = translator.translate(chunk['content'],row.source_language,row.language,attempt=row.attempts)
        translations.validate_translation(chunk['content'],text,row.source_language,row.language)
        if not lost.is_set():
            translations.finish(row,text=text)
    except Exception as exc:
        code = str(exc) if isinstance(exc, translations.TranslationError) else 'model_unavailable'
        if code not in {'empty_output','numbers_mismatch','links_mismatch','table_structure_mismatch',
                        'input_too_large','output_truncated','model_repetition'}:
            code = 'model_unavailable'
        if not lost.is_set():
            translations.finish(row,error=code)
        logger.warning('translation_failed id=%s chunk=%s language=%s reason=%s type=%s',
                       row.id,row.chunk_id,row.language,code,type(exc).__name__)
        diagnostic = getattr(exc, 'diagnostic', None)
        if diagnostic and diagnostic.get('kind') == 'ollama_http_error':
            logger.warning('translation_http_error id=%s status=%s response_sha256=%s',
                           row.id, diagnostic['http_status'], diagnostic.get('response_sha256'))
        # Bounded, explicit diagnostics remain in the existing private database.
        # Never put source passages or rejected candidate translations in logs.
        if diagnostic_budget and diagnostic_budget[0] > 0 and getattr(exc, 'diagnostic', None):
            with store.session() as db:
                db.merge(store.TranslationDiagnostic(id=row.id, language=row.language,
                    document_id=row.document_id, chunk_id=row.chunk_id, payload=exc.diagnostic))
                db.commit()
            diagnostic_budget[0] -= 1
        if code == 'model_unavailable':
            raise ModelUnavailable('model_unavailable') from None
    finally:
        stop.set()
        thread.join(timeout=2)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backfill', action='store_true', help='Queue six languages for current published chunks (idempotent)')
    parser.add_argument('--queue-only', action='store_true', help='Prepare queue without loading model weights')
    parser.add_argument('--status', action='store_true', help='Print current-version status counts without model work')
    parser.add_argument('--retry-failed', action='store_true', help='Explicitly reset exhausted failures')
    parser.add_argument('--watch', action='store_true', help='Keep polling for future publications')
    parser.add_argument('--document', help='Limit backfill and inference to one document ID')
    parser.add_argument('--language', choices=sorted(LANG_NAMES), help='Only claim/report/reset this target language')
    parser.add_argument('--diagnostics-limit', type=int, default=0, help='Maximum private failed-segment samples to save (0 disables)')
    parser.add_argument('--limit', type=int, default=0, help='Maximum attempts this invocation; 0 drains queue')
    parser.add_argument('--max-seconds', type=int, default=0, help='Stop between chunks after this duration; queued work is retained')
    parser.add_argument('--device', choices=['auto','cpu','mps','cuda'], default='auto')
    parser.add_argument('--local-files-only', action='store_true', help='Load previously downloaded model without network')
    parser.add_argument('--cloud-db', action='store_true', help='Use existing gcloud credentials and Cloud SQL proxy at localhost:54329')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.cloud_db:
        from scripts.cloud_database import connect
        connect()
    # Only additive schema creation; no account bootstrap or web sessions.
    store.ChunkTranslation.__table__.create(store.engine(), checkfirst=True)
    if args.diagnostics_limit:
        if not 0 < args.diagnostics_limit <= 50:
            parser.error('--diagnostics-limit must be between 0 and 50')
        store.TranslationDiagnostic.__table__.create(store.engine(), checkfirst=True)
    if args.backfill:
        print(json.dumps(translations.backfill(args.document)), flush=True)
    if args.retry_failed:
        print(json.dumps({'requeued':translations.retry_failed(args.document, args.language)}), flush=True)
    if args.status or args.queue_only:
        print(json.dumps(translations.statistics(args.document, args.language)), flush=True)
        return
    execution = os.environ.get('CLOUD_RUN_EXECUTION')
    if execution:
        store.TranslationBatch.__table__.create(store.engine(), checkfirst=True)
        if batch_halted(execution):
            print(json.dumps({'stop_reason':'batch_halted'}), flush=True)
            raise SystemExit(2)
    # Later tasks in a finite batch need not load weights after the queue drains.
    counts = translations.statistics(args.document, args.language)
    if not args.watch and not counts.get('queued') and not counts.get('running'):
        print(json.dumps({'stop_reason':'queue_drained','status':counts}), flush=True)
        return
    try:
        if settings.TRANSLATION_RUNTIME == 'ollama':
            from app.services.ollama_translation import OllamaTranslator
            translator = OllamaTranslator()
        else:
            from app.services.local_translation import LocalTranslator
            translator = LocalTranslator(args.device, args.local_files_only)
    except Exception as exc:
        batch_halted(execution, halt=True)
        logger.error('translation_model_init_failed type=%s', type(exc).__name__)
        raise SystemExit(2) from None
    done = 0
    diagnostic_budget = [args.diagnostics_limit]
    print(json.dumps({'initial_status':translations.statistics(args.document, args.language),
                      'language':args.language}), flush=True)
    started = time.monotonic()
    while not args.limit or done < args.limit:
        if args.max_seconds and time.monotonic()-started >= args.max_seconds:
            break
        try:
            processed = process_one(translator, args.document, args.language, diagnostic_budget)
        except ModelUnavailable:
            batch_halted(execution, halt=True)
            print(json.dumps({'stop_reason':'model_unavailable',
                              'status':translations.statistics(args.document, args.language)}), flush=True)
            raise SystemExit(2)
        if processed:
            done += 1
            print(json.dumps({'attempts_this_run':done, 'language':args.language,
                              'status':translations.statistics(args.document, args.language)}), flush=True)
            continue
        counts = translations.statistics(args.document, args.language)
        if not args.watch and not counts.get('queued') and not counts.get('running'):
            break
        time.sleep(5)
    print(json.dumps({'status':translations.statistics(args.document, args.language)}), flush=True)


if __name__ == '__main__':
    main()
