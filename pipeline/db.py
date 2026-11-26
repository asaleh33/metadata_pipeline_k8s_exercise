"""
PostgreSQL: what the pipeline knows about every image, in two tables.

    images             one row per image: status, category, confidence, classifier, time,
                       and ALL its metadata (the enriched JSON) in the column `metadata`
    selected_metadata  one row per (image, key) for the chosen keys (variables.json),
                       as a number and a unit (or a text), ready to compare and sort

    images.image ──< selected_metadata.image      (one image, several keys)

Two helper functions make any metadata value usable in SQL:
    num('3.198 mm')  -> 3.198          unit('3.198 mm') -> 'mm'
so   num(metadata->>'AP_MAG')   is the magnification of an image, as a number.

The tables are created on first use. Running an image again replaces its rows.
"""
import os
import time

import psycopg
from psycopg.types.json import Jsonb

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sem:sem@localhost:5432/sem")

SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    image         TEXT PRIMARY KEY,           -- file name without extension
    source        TEXT,                       -- path of the TIFF
    status        TEXT NOT NULL,              -- OK or ERROR
    n_keys        INTEGER,                    -- metadata keys found in the TIFF
    category      TEXT,                       -- from the classifier
    confidence    REAL,
    classifier    TEXT,                       -- model that gave the category
    metadata      JSONB,                      -- the whole enriched JSON
    processed_at  TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS selected_metadata (
    image  TEXT REFERENCES images(image) ON DELETE CASCADE,
    key    TEXT,                              -- e.g. AP_WD
    value  DOUBLE PRECISION,                  -- e.g. 3.198   (NULL if missing or not a number)
    unit   TEXT,                              -- e.g. mm
    text   TEXT,                              -- e.g. InLens  (a value that is not a number)
    PRIMARY KEY (image, key)
);
-- '3.198 mm' -> 3.198 ; 'Mag =  21.59 K X' -> 21.59 ; 'InLens' -> NULL
CREATE OR REPLACE FUNCTION num(t TEXT) RETURNS DOUBLE PRECISION
    LANGUAGE sql IMMUTABLE AS
    $$ SELECT (regexp_match(t, '([-+]?[0-9]+(?:\\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)'))[1]::double precision $$;
-- '3.198 mm' -> 'mm'
CREATE OR REPLACE FUNCTION unit(t TEXT) RETURNS TEXT
    LANGUAGE sql IMMUTABLE AS
    $$ SELECT trim((regexp_match(t, '[-+]?[0-9]+(?:\\.[0-9]+)?(?:[eE][-+]?[0-9]+)?\\s*(.*)$'))[1]) $$;
"""


def connect(wait_s=None):
    """Connects (waiting for the database to start) and creates the tables if needed.

    It waits up to DB_WAIT_SECONDS (default 600 s): on a new cluster the database
    may need minutes before it answers, for example while its image is downloaded."""
    wait_s = wait_s if wait_s is not None else int(os.getenv("DB_WAIT_SECONDS", "600"))
    deadline = time.time() + wait_s
    while True:
        try:
            conn = psycopg.connect(DATABASE_URL, autocommit=True)
            conn.execute(SCHEMA)
            return conn
        except psycopg.OperationalError:
            if time.time() > deadline:
                raise SystemExit(f"cannot connect to the database at {DATABASE_URL.split('@')[-1]} after {wait_s} s")
            print("waiting for the database ...")
            time.sleep(2)


def _number(text):
    """'3.18' -> 3.18, 'N/A' -> None."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def save_image(conn, record, rows, metadata=None):
    """Writes one image (insert or replace), its whole metadata, and its selected keys [(key, value, unit), ...]."""
    values = {"category": None, "confidence": None, "classifier": None, **record,
              "metadata": Jsonb(metadata) if metadata else None}
    with conn.transaction():
        conn.execute(
            """INSERT INTO images (image, source, status, n_keys, category, confidence, classifier, metadata, processed_at)
               VALUES (%(image)s, %(source)s, %(status)s, %(n_keys)s, %(category)s, %(confidence)s, %(classifier)s,
                       %(metadata)s, now())
               ON CONFLICT (image) DO UPDATE SET
                   source = EXCLUDED.source, status = EXCLUDED.status, n_keys = EXCLUDED.n_keys,
                   category = EXCLUDED.category, confidence = EXCLUDED.confidence,
                   classifier = EXCLUDED.classifier, metadata = EXCLUDED.metadata, processed_at = now()""",
            values)
        conn.execute("DELETE FROM selected_metadata WHERE image = %s", (record["image"],))
        for key, value, unit in rows:
            number = _number(value)
            text = value if number is None and value != "N/A" else None
            conn.execute("INSERT INTO selected_metadata (image, key, value, unit, text) VALUES (%s, %s, %s, %s, %s)",
                         (record["image"], key, number, unit if unit not in ("N/A", "") else None, text))


def list_images(conn):
    """All images with their category, newest first."""
    cur = conn.execute("SELECT image, status, category, confidence, processed_at FROM images ORDER BY processed_at DESC")
    return [dict(zip(("image", "status", "category", "confidence", "processed_at"), r)) for r in cur.fetchall()]


def ask(conn, keys):
    """For every image, the value of each key (any metadata key, not only the selected ones)."""
    columns = ", ".join("metadata->>%s" for _ in keys)
    cur = conn.execute(f"SELECT image, category, {columns} FROM images WHERE status = 'OK' ORDER BY image", keys)
    return [{"image": r[0], "category": r[1], **dict(zip(keys, r[2:]))} for r in cur.fetchall()]


def find_keys(conn, part=""):
    """Metadata keys present in the database whose name contains `part`, with how many images have them."""
    cur = conn.execute("""SELECT key, count(*) FROM images, jsonb_object_keys(metadata) AS key
                          WHERE key ILIKE %s GROUP BY key ORDER BY key""", (f"%{part}%",))
    return cur.fetchall()
