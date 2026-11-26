"""
The whole pipeline as a REST API: send one SEM image, get its enriched metadata back.

    bentoml serve api:SemPipeline --port 3001        page: http://localhost:3001

Used by Compose (service `upload`, step 7) and by Kubernetes (k8s-api.yaml, step 8).

    POST /process   an image (and optionally its name)  -> status, category, selected metadata
    POST /images    nothing                             -> every image in the database
    POST /ask       a list of metadata keys             -> their values, for every image

The same chain as run_batch.py (process.py), for one image at a time.
"""
import re
import shutil
import threading
from pathlib import Path

import bentoml

import db
import process


@bentoml.service(traffic={"timeout": 180})
class SemPipeline:
    def __init__(self) -> None:
        self.conn = db.connect()
        # requests from several users arrive in parallel; the chain (semmeta's cleaner, the database
        # connection) handles one image at a time, so images are processed one after the other
        self.lock = threading.Lock()

    @bentoml.api
    def process(self, image: Path, name: str = "") -> dict:
        # BentoML saves the upload as tmp<8 characters><original name>: recover the name
        original = re.sub(r"^tmp[a-z0-9_]{8}", "", image.name) or image.name
        name = name or Path(original).stem
        # keep a copy of the uploaded file next to the outputs (the temporary file is deleted)
        uploads = Path(process.OUTPUT_DIR) / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        saved = uploads / original
        with self.lock:
            shutil.copyfile(image, saved)
            record = process.process_image(saved, self.conn, name=name)
            rows = self.conn.execute("SELECT key, value, unit, text FROM selected_metadata WHERE image = %s ORDER BY key",
                                     (name,)).fetchall()
        return {**record, "metadata": [{"key": k, "value": v if t is None else t, "unit": u} for k, v, u, t in rows]}

    @bentoml.api
    def images(self) -> list:
        with self.lock:
            return [{**r, "processed_at": r["processed_at"].isoformat(timespec="seconds")} for r in db.list_images(self.conn)]

    @bentoml.api
    def ask(self, keys: list[str]) -> list:
        with self.lock:
            return db.ask(self.conn, keys)
