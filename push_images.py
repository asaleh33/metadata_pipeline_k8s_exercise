"""
Push SEM images to the pipeline's REST API, as several users would do at the same time.

    python push_images.py imgs                       every TIFF in a folder (and its subfolders)
    python push_images.py a.tif b.tif --users 4      some files, 4 users sending in parallel
    python push_images.py imgs --url http://localhost:3002

Each image is sent to POST <url>/process as a file upload (multipart/form-data), exactly as
    curl -X POST <url>/process -F image=@a.tif
The API runs the whole chain and answers with the image's status, category and chosen metadata.
"""
import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def find_images(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in (".tif", ".tiff"))
        elif p.is_file():
            files.append(p)
    return files


def push(url, path):
    start = time.time()
    with open(path, "rb") as f:
        response = requests.post(f"{url}/process", files={"image": (path.name, f, "image/tiff")}, timeout=600)
    response.raise_for_status()
    return path, response.json(), time.time() - start


def main():
    parser = argparse.ArgumentParser(description="Send SEM images to the pipeline's REST API.")
    parser.add_argument("paths", nargs="+", help="TIFF files or folders")
    parser.add_argument("--url", default=os.getenv("PIPELINE_URL", "http://localhost:3002"))
    parser.add_argument("--users", type=int, default=4, help="images sent at the same time")
    args = parser.parse_args()

    requests.get(f"{args.url}/readyz", timeout=10).raise_for_status()      # is the API up?
    images = find_images(args.paths)
    print(f"{len(images)} images -> {args.url}/process, {args.users} users in parallel\n")
    print(f"{'IMAGE':<26} {'STATUS':<7} {'CATEGORY':<28} {'CONF.':<7} SECONDS")

    start, results = time.time(), []
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        for future in as_completed([pool.submit(push, args.url, p) for p in images]):
            path, r, seconds = future.result()
            results.append(r)
            print(f"{r['image'][:25]:<26} {r['status']:<7} {(r.get('category') or '-'):<28} "
                  f"{str(r.get('confidence') or '-'):<7} {seconds:.1f}")

    ok = sum(r["status"] == "OK" for r in results)
    print(f"\n{ok} OK, {len(results) - ok} ERROR, in {time.time() - start:.1f} s")


if __name__ == "__main__":
    main()
