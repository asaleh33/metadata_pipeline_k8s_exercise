"""
One SEM image through the whole chain.

    TIFF ──► semmeta extractor ──► <name>_raw.json        all instrument metadata (tag 34118)
         ──► semmeta cleaner   ──► <name>_cleaned.json    "WD = 3.18 mm" -> "3.18 mm"
         ──► BentoML classifier──► category, confidence, model
         ──► enrichment        ──► <name>_enriched.json   cleaned metadata + classification
         ──► semmeta visualizer──► <name>.png and a table in the terminal
         ──► PostgreSQL        ──► one row in `images` (with all metadata), the chosen keys in `selected_metadata`

Used by run_batch.py (a folder) and api.py (one uploaded image).
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

import db
from semmeta import CLEANER, SEMMeta, SEMVisualizer

CLASSIFIER_URL = os.getenv("CLASSIFIER_URL", "http://localhost:3000")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
VARIABLES_FILE = os.getenv("VARIABLES_FILE", "variables.json")


def load_variables():
    """The keys to show and store, from variables.json; None = the visualizer's default list."""
    try:
        return json.loads(Path(VARIABLES_FILE).read_text())["variables"] or None
    except FileNotFoundError:
        return None


def wait_for_classifier(timeout_s=300):
    """Waits until the classifier answers /readyz (its model is loaded)."""
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            if requests.get(f"{CLASSIFIER_URL}/readyz", timeout=5).status_code == 200:
                return
        except requests.RequestException:      # not started yet, or still loading the model
            pass
        print("waiting for the classifier ...")
        time.sleep(5)
    raise SystemExit(f"the classifier at {CLASSIFIER_URL} is not ready after {timeout_s} s")


def classify(image_path):
    """Sends the image file to the BentoML service, as `curl -F image=@file` does."""
    with open(image_path, "rb") as f:
        response = requests.post(f"{CLASSIFIER_URL}/classify",
                                 files={"image": (Path(image_path).name, f)}, timeout=120)
    response.raise_for_status()
    return response.json()          # {"category": ..., "confidence": ..., "model": ...}


def process_image(image_path, conn, name=None):
    """Runs the chain on one image; returns a short record (also stored in the database)."""
    name = name or Path(image_path).stem
    out = Path(OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {name}  ({image_path})")

    # 1. metadata extraction (semmeta)
    metadata = SEMMeta.ExtractMetadata(str(image_path))
    if not metadata:
        print("  ERROR: not a readable image, or no instrument metadata (tag 34118)")
        record = {"image": name, "source": str(image_path), "status": "ERROR", "n_keys": 0}
        db.save_image(conn, record, rows=[])
        return record
    raw_json = out / f"{name}_raw.json"
    SEMMeta.WriteSEMJson(raw_json, metadata)

    # 2. cleaning (semmeta)
    cleaned = CLEANER.process(raw_json)
    cleaned_json = out / f"{name}_cleaned.json"
    CLEANER.save_cleaned(cleaned_json)
    print(f"  metadata : {len(metadata)} keys -> {raw_json.name}, {cleaned_json.name}")

    # 3. classification (BentoML)
    result = classify(image_path)
    classification = {**result, "classified_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    print(f"  category : {result['category']}  (confidence {result['confidence']}, model {result['model']})")

    # 4. enrichment: the cleaned metadata plus the classification, in a new file
    enriched = {**cleaned, "classification": classification}
    enriched_json = out / f"{name}_enriched.json"
    enriched_json.write_text(json.dumps(enriched, indent=2) + "\n")   # end with a newline, like any text file
    print(f"  enriched : {enriched_json.name}")

    # 5. figure and terminal table (semmeta)
    visualizer = SEMVisualizer(json_path=cleaned_json, image_path=str(image_path), output_dir=str(out),
                               variables=load_variables())
    figure = visualizer.show_image_with_table()
    print(f"  figure   : {Path(figure).name}")

    # 6. database: all metadata (JSONB) and the selected keys as number + unit
    record = {"image": name, "source": str(image_path), "status": "OK", "n_keys": len(metadata),
              "category": result["category"], "confidence": result["confidence"], "classifier": result["model"]}
    db.save_image(conn, record, rows=visualizer.extract_variables(), metadata=enriched)
    return record
