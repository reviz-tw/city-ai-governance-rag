"""Operator inspection from authenticated Cloud Shell; never prints credentials.

Requires cloud-sql-python-connector[pg8000] in the operator environment only.
Read-only unless an explicit expected count requests a one-time English repair.
"""
import argparse
import json
import subprocess
import time
from urllib.parse import urlparse, unquote
from google.oauth2.credentials import Credentials
from google.cloud.sql.connector import Connector


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--limit',type=int,default=8)
    p.add_argument('--requeue-known-english-failures',type=int,metavar='EXPECTED_COUNT')
    p.add_argument('--translation', help='Inspect one current English translation and its private diagnostic')
    p.add_argument('--requeue-http-failure', action='store_true', help='Explicitly retry only the selected model_unavailable row once')
    args=p.parse_args()
    if args.requeue_http_failure and (not args.translation or args.requeue_known_english_failures is not None):
        p.error('--requeue-http-failure requires --translation and cannot reset other failures')
    if not 0 <= args.limit <= 50:
        p.error('limit must be 0..50')
    if args.requeue_known_english_failures is not None and not 1 <= args.requeue_known_english_failures <= 50:
        p.error('one-time repair must name the expected count, between 1 and 50')
    def gcloud(*parts):
        return subprocess.check_output(['gcloud',*parts,'--project=tdf-ocf','--quiet'],text=True).strip()
    token=gcloud('auth','print-access-token')
    url=urlparse(gcloud('secrets','versions','access','latest','--secret=city-governance-database-url'))
    with Connector(credentials=Credentials(token),refresh_strategy='LAZY') as connector:
        conn=connector.connect('tdf-ocf:asia-east1:city-governance-postgres','pg8000',
                               user=unquote(url.username),password=unquote(url.password),
                               db=url.path.lstrip('/'),timeout=30)
        try:
            cursor=conn.cursor()
            if args.requeue_http_failure:
                cursor.execute("SELECT t.status,t.error FROM chunk_translations t JOIN documents d ON d.id=t.document_id AND d.published_version=t.version WHERE t.id=%s AND t.language='en' AND t.model=%s AND t.rules_version=%s FOR UPDATE OF t",(args.translation,'translategemma:12b','chunk-translation-ollama-v1'))
                row=cursor.fetchone()
                if tuple(row or ()) != ('failed','model_unavailable'):
                    raise SystemExit(f'Selected row is not a failed model_unavailable translation: {row}; no changes')
                cursor.execute("UPDATE chunk_translations SET status='queued',attempts=0,error=NULL,retry_at=0,lease_token=NULL,lease_until=0,priority=100,updated_at=%s WHERE id=%s",(time.time(),args.translation))
                conn.commit()
                print(json.dumps({'explicit_one_time_http_requeue':args.translation}),flush=True)
            elif args.requeue_known_english_failures is None:
                cursor.execute('SET TRANSACTION READ ONLY')
            else:
                cursor.execute("SELECT t.id FROM chunk_translations t JOIN documents d ON d.id=t.document_id AND d.published_version=t.version WHERE t.language='en' AND t.status='failed' AND t.error IN ('numbers_mismatch','model_unavailable') AND t.model=%s AND t.rules_version=%s FOR UPDATE OF t",('translategemma:12b','chunk-translation-ollama-v1'))
                ids=[r[0] for r in cursor.fetchall()]
                if len(ids) != args.requeue_known_english_failures:
                    raise SystemExit(f'Expected {args.requeue_known_english_failures} failures, found {len(ids)}; no changes committed')
                cursor.execute("UPDATE chunk_translations SET status='queued',attempts=0,error=NULL,retry_at=0,lease_token=NULL,lease_until=0,priority=20,updated_at=%s WHERE id=ANY(%s)",(time.time(),ids))
                conn.commit()
                print(json.dumps({'explicit_one_time_english_requeue':len(ids)}),flush=True)
            cursor.execute("SELECT t.language,t.status,count(*) FROM chunk_translations t JOIN documents d ON d.id=t.document_id AND d.published_version=t.version WHERE t.model=%s AND t.rules_version=%s GROUP BY t.language,t.status ORDER BY 1,2",('translategemma:12b','chunk-translation-ollama-v1'))
            print(json.dumps({'counts':cursor.fetchall()},ensure_ascii=False),flush=True)
            if args.translation:
                cursor.execute("SELECT t.id,t.document_id,t.chunk_id,t.status,t.error,x.payload FROM chunk_translations t JOIN documents d ON d.id=t.document_id AND d.published_version=t.version LEFT JOIN translation_diagnostics x ON x.id=t.id WHERE t.id=%s AND t.language='en'",(args.translation,))
                print(json.dumps({'selected_translation':cursor.fetchone()},ensure_ascii=False),flush=True)
            if args.limit:
                cursor.execute('SELECT id,document_id,chunk_id,payload FROM translation_diagnostics WHERE language=%s ORDER BY created_at LIMIT %s',('en',args.limit))
                for row in cursor.fetchall():
                    print(json.dumps({'id':row[0],'document':row[1],'chunk':row[2],'sample':row[3]},ensure_ascii=False),flush=True)
        finally:
            conn.rollback()
            conn.close()


if __name__=='__main__':
    main()
