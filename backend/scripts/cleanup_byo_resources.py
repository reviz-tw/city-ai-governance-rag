"""Cleanup script for isolated BYO chunk validation resources in project tdf-ocf.

Deletes ONLY the temporary test engine, test dataStore, and synthetic GCS files.
NEVER touches production datastore (city-governance-datastore) or production documents.
"""
import json
import subprocess
import time
import urllib.error
import urllib.request
from google.cloud import storage
from google.oauth2.credentials import Credentials

PROJECT = "tdf-ocf"
BASE = "https://discoveryengine.googleapis.com/v1alpha/projects/tdf-ocf/locations/global/collections/default_collection"
ENGINE_ID = "city-chunk-validation-20260916"
DATA_STORE_ID = "city-governance-chunk-validation-20260916-v2"
BUCKET_NAME = "tdf-ocf-city-governance-docs"
PREFIX = "validation/20260916-chunks"


def token() -> str:
    return subprocess.run(
        ["gcloud", "auth", "print-access-token", "--account", "hcchien@reviz.tw"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def api_call(url: str, method: str = "GET") -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token()}", "x-goog-user-project": PROJECT},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            content = resp.read()
            return json.loads(content.decode("utf-8")) if content else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return {"http_status": exc.code, "error": body}


def wait_for_lro(op_name: str, max_wait: int = 120):
    for _ in range(max_wait // 5):
        res = api_call(f"https://discoveryengine.googleapis.com/v1alpha/{op_name}")
        if res.get("done"):
            return res
        time.sleep(5)
    return {"timeout": True}


def run_cleanup():
    results = {}
    tok = token()

    # 1. Delete Engine
    print(f"1. Deleting Engine {ENGINE_ID}...")
    engine_del = api_call(f"{BASE}/engines/{ENGINE_ID}", method="DELETE")
    results["delete_engine"] = engine_del
    if engine_del.get("name"):
        wait_res = wait_for_lro(engine_del["name"])
        results["delete_engine_lro"] = wait_res
        print("   Engine deletion operation completed.")
    else:
        print(f"   Engine response: {engine_del}")

    # 2. Delete DataStore
    print(f"2. Deleting DataStore {DATA_STORE_ID}...")
    store_del = api_call(f"{BASE}/dataStores/{DATA_STORE_ID}", method="DELETE")
    results["delete_data_store"] = store_del
    if store_del.get("name"):
        wait_res = wait_for_lro(store_del["name"])
        results["delete_data_store_lro"] = wait_res
        print("   DataStore deletion operation completed.")
    else:
        print(f"   DataStore response: {store_del}")

    # 3. Delete GCS test validation chunks
    print(f"3. Deleting GCS objects under gs://{BUCKET_NAME}/{PREFIX}/ ...")
    client = storage.Client(project=PROJECT, credentials=Credentials(tok))
    bucket = client.bucket(BUCKET_NAME)
    blobs = list(bucket.list_blobs(prefix=PREFIX))
    deleted_blobs = []
    for b in blobs:
        b.delete()
        deleted_blobs.append(b.name)
    results["deleted_gcs_blobs"] = deleted_blobs
    print(f"   Deleted {len(deleted_blobs)} test GCS blobs.")

    print("\nCleanup summary:")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


if __name__ == "__main__":
    run_cleanup()
