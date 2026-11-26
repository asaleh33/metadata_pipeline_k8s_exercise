"""
Batch: every SEM image in a folder (and its subfolders), once.

    python run_batch.py [folder]          default: $INPUT_DIR, else imgs

Needs the classifier (CLASSIFIER_URL) and PostgreSQL (DATABASE_URL).
Writes the JSON files, the figures and processing_report.txt into OUTPUT_DIR.
"""
import glob
import os
import sys

import db
import process
from semmeta import SEMMeta


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.getenv("INPUT_DIR", "imgs")
    images = sorted(f for f in glob.iglob(os.path.join(folder, "**", "*"), recursive=True)
                    if os.path.isfile(f) and f.endswith(SEMMeta.semext))
    print(f"{len(images)} SEM images in {folder}")

    conn = db.connect()
    process.wait_for_classifier()

    records = [process.process_image(path, conn) for path in images]

    report = os.path.join(process.OUTPUT_DIR, "processing_report.txt")
    SEMMeta.WriteProcessingReport(report, [{"image": r["source"], "status": r["status"]} for r in records])

    print(f"\n{'IMAGE':<26} {'STATUS':<7} {'CATEGORY':<28} CONFIDENCE")
    for r in records:
        print(f"{r['image'][:25]:<26} {r['status']:<7} {r.get('category') or '-':<28} {r.get('confidence') or '-'}")
    n = conn.execute("SELECT count(*) FROM images").fetchone()[0]
    print(f"\nreport: {report}\ndatabase: {n} images in table 'images'")


if __name__ == "__main__":
    main()
