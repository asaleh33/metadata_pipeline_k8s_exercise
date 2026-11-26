# From a microscope file to a database: an automated SEM pipeline

*Tools for Data Management and Curation · Lecturer: Stefano Cozzini · Tutor: Ahmed Khalil · about 2 hours*

A scanning electron microscope (SEM) saves each image as a TIFF file. Hidden inside every file are **hundreds of instrument parameters**: working distance, beam current, pixel size, detector, and more. Nobody reads them by hand, so they are easily lost for search and reuse.

In this exercise you run a small **automated pipeline** that turns each SEM image into **findable, enriched metadata**: it reads the hidden parameters, asks an AI model what the image shows, writes everything into a JSON file and a figure, and stores the essentials in a database that you can query. The whole pipeline runs in **containers**, first with **Docker Compose** on your laptop, then on **Kubernetes**, where at the end it also accepts new images sent by its users through a **REST API**.

---

## Where this exercise comes from

This exercise is a small, modern version of a pipeline built in 2019 for CNR-IOM for the **NFFA-EUROPE** project, in the Master in High Performance Computing (MHPC) thesis *Data Management Tools for NFFA-EUROPE Project* by **Ahmed Khalil**, supervised by **Stefano Cozzini** ([project page](https://www.mhpc.it/student-projects/data-management-tools-nffa-europe-project), [thesis PDF](https://www.mhpc.it/sites/default/files/media/docs/2026-07/Saleh%2BHossanin.pdf)).

The goal then was to organise the SEM images arriving from the NFFA-EUROPE partners (about 150,000 images from CNR-IOM alone) in a FAIR way (Wilkinson et al., 2016). Each image went through four steps:

1. **extracting the metadata** stored in the TIFF file (standard tags and the instrument tag 34118);
2. **measuring the scale bar with OCR**, to compute the pixel size when the instrument did not record it;
3. **classifying the image** with a neural network pre-trained on SEM images;
4. **storing all results in a MySQL database**, browsable through phpMyAdmin.

To process large datasets, the code ran in parallel with Apache Spark, in **Docker containers orchestrated by Kubernetes**, on OpenStack and on the C3HPC cluster (one master and eight worker nodes of 24 cores each, 192 worker cores in total):

<p align="center"><a href="docs/thesis_2019_architecture.png"><img src="docs/thesis_2019_architecture.png" width="100%" alt="2019 architecture: a Kubernetes-Spark cluster of one master and eight workers, each running Docker and reading the SEM images from a Lustre file system, all writing to a MySQL database shown with phpMyAdmin"></a><br><sub>Click the figure to open it at full resolution.</sub></p>

<p align="center"><i>The 2019 Kubernetes-Spark cluster on C3HPC (thesis, Figure 3.5): one master and eight workers, each in Docker; the SEM images on a shared Lustre file system; the results in MySQL, shared through phpMyAdmin.</i></p>

Today's exercise keeps the same idea, with today's tools and at laptop size:

| Part | 2019 thesis | This exercise |
|---|---|---|
| Metadata extraction | Python + Pillow, tag 34118 | `semmeta`, the package from Python for Data Management I |
| Pixel size from the scale bar | OCR with OpenCV + Tesseract | not included |
| Classification | TensorFlow model, inside the code | Vision Transformer served by **BentoML**, as its own service |
| Database and browser view | MySQL + phpMyAdmin | **PostgreSQL** + **Adminer** |
| Running it | Spark on a Kubernetes cluster | **Docker Compose**, then **Kubernetes** (kind) on your laptop |

---

## Docker and Kubernetes in two minutes

<p align="center"><img src="docs/docker-logo.svg" height="80" alt="Docker logo">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src="docs/kubernetes-logo.svg" height="80" alt="Kubernetes logo"></p>

**Docker** packs a program together with everything it needs (Python, libraries, a model) into an **image**, and runs that image as a **container**: an isolated box that behaves the same on every computer. **Docker Compose** starts several containers together on **one** computer, from one file (`compose.yaml`), and lets them find each other by name.

**Kubernetes** (Greek for *helmsman*) is an **open-source** system created at Google and released in 2014, now maintained by the Cloud Native Computing Foundation (CNCF). It runs containers on a **cluster** of computers. You describe what you want ("one database, one classifier, run the pipeline once"), and Kubernetes makes it happen and keeps it so: it places containers on machines, restarts them when they fail, and only sends work to a container once it is ready (Burns et al., 2016). Its containers run inside **pods**.

**Docker builds and runs the boxes; Kubernetes decides where they run and keeps them running.** The same two images you build with Docker in step 0 run unchanged under Compose (steps 1–5) and under Kubernetes (step 6).

---

## The pipeline of this exercise

<p align="center"><a href="docs/architecture.svg"><img src="docs/architecture.svg" width="100%" alt="Architecture: SEM TIFF images and variables.json go into the pipeline container (1 extract, 2 clean, 3 classify via the classifier container, 4 enrich, 5 draw, 6 store); out come the output folder with the enriched JSON and the PNG figure per image, and the PostgreSQL database that you query"></a><br><sub>A vector figure: it stays sharp at any zoom. Click it to open it on its own page.</sub></p>

### What goes in, what comes out

| Direction | What | Where |
|---|---|---|
| **In** | SEM images, TIFF, in any subfolder | `imgs/` |
| **In** (optional) | the list of metadata keys to show and store | `variables.json` |
| **Out**, per image | `<name>_enriched.json`: all instrument metadata, cleaned, plus the category from the AI model | `output/` |
| **Out**, per image | `<name>.png`: the image with a table of the chosen keys below it | `output/` |
| **Out**, all images | the database: one row per image, all its metadata, the chosen keys as number + unit | PostgreSQL |
| Kept for traceability | `<name>_raw.json`, `<name>_cleaned.json`, `processing_report.txt` | `output/` |

### The three containers

| Container | Role | Built from |
|---|---|---|
| **pipeline** | runs the six steps for every image, then stops | `pipeline/` (`semmeta` + `process.py`) |
| **classifier** | a web service: receives an image, answers its category | `classifier/` (BentoML `service.py`, the model inside the image) |
| **db** | PostgreSQL: keeps the results, answers SQL queries | the official `postgres` image |

A fourth container, **adminer**, is a web page to browse the database.

---

## Conventions

Terminal panels follow the usual `console` notation: lines with the `$` prompt are input, every other line is an example of the output of the command above it. Yours may differ in details such as versions, IDs, times, or download lines for images you already have. Values that depend on your run are written as `x`, and omitted lines as `...`. Unless a step says otherwise, run commands from the repository root.

```console
$ docker --version
Docker version 2x.x.x, build xxxxxxx
```

## Plan (2 hours)

| Part | Time | Steps |
|---|---|---|
| Set up: Python environment, images, kind (build the images before the class if you can) | 20 min | 0 |
| The pipeline with Docker Compose | 20 min | 1–3 |
| Your own metadata, and the database | 25 min | 4–5 |
| Kubernetes | 30 min | 6 |
| Upload an image on a web page | 10 min | 7 |
| Send images to the deployed pipeline through its REST API | 15 min | 8 |

## The folder

```text
metadata-pipeline/
├── README.md
├── .env.example            the database settings: copy it to .env (step 0.2)
├── .gitignore              what git never commits: .env, output/, ...
├── compose.yaml            the containers on one computer (Docker Compose)
├── k8s.yaml                the same on Kubernetes
├── k8s-api.yaml            step 8: the pipeline's REST API on Kubernetes
├── push_images.py          step 8: send TIFF images to the REST API, as several users
├── variables.json          the metadata keys to show and store (you can edit it)
├── requirements.txt        the packages of the Python environment sem-auto
├── imgs/                   4 example SEM images (TIFF)
├── classifier/
│   ├── service.py          the BentoML classifier (unchanged from the BentoML exercise)
│   └── Dockerfile
├── pipeline/
│   ├── semmeta/            our package: extractor, cleaner, visualizer
│   ├── tests/              its tests
│   ├── process.py          the six steps for one image
│   ├── run_batch.py        all images of a folder, once
│   ├── db.py               the database tables
│   ├── ask.py              ask the database for any metadata key
│   ├── api.py              the pipeline as a REST API (steps 7 and 8)
│   ├── requirements.txt
│   └── Dockerfile
├── docs/                   figures of this guide
└── output/                 created by the pipeline
```

All commands run from `metadata-pipeline`.

---

## Step 0: set up

The first build downloads about 1.5 GB (Python, torch, the AI model).

### 0.1 A Python environment for the exercise: sem-auto

The pipeline itself runs in containers, but a few tools run on your laptop: the tests of `semmeta`, and `ask.py`, which queries the database. They get their own environment, `sem-auto`, so nothing else on your laptop changes, even if you already have these packages.

```console
$ git clone <repository URL> metadata-pipeline
Cloning into 'metadata-pipeline'...
...
$ cd metadata-pipeline

$ python3.12 -m venv ~/venvs/sem-auto --prompt sem-auto
$ source ~/venvs/sem-auto/bin/activate
$ python -m pip install --upgrade pip
Successfully installed pip-2x.x

$ pip install -r requirements.txt
Successfully installed ... matplotlib-x.x pillow-x.x psycopg-x.x pytest-x.x requests-x.x

$ python -m pytest -q -p no:cacheprovider pipeline/tests
......                                                                   [100%]
6 passed in x.xxs
```

Your prompt now starts with `(sem-auto)`. In every new terminal, activate it again with `source ~/venvs/sem-auto/bin/activate`.

### 0.2 Build the two images

The first build takes about 10–15 minutes, mostly to download torch and the model.

```console
$ mkdir -p output
$ cp .env.example .env
$ echo "HOST_UID=$(id -u)" >> .env
$ echo "HOST_GID=$(id -g)" >> .env
$ grep -v "^#" .env                 # the file without its comment lines
POSTGRES_USER=sem
POSTGRES_PASSWORD=sem
POSTGRES_DB=sem
HOST_UID=1000
HOST_GID=1000

$ docker compose --profile batch build
 ✔ Image sem-classifier:1.0  Built
 ✔ Image sem-pipeline:1.0    Built

$ docker images | grep -E "sem-classifier|sem-pipeline"
sem-classifier   1.0   xxxxxxxxxxxx   x seconds ago   ~2GB
sem-pipeline     1.0   xxxxxxxxxxxx   x seconds ago   ~400MB
```

- `sem-classifier` holds Python, CPU torch, BentoML, `service.py` **and the model**, downloaded once during the build. It never needs the internet again, so its pods can start anywhere, even on a cluster without internet access.
- `sem-pipeline` holds Python, `semmeta`, the pipeline code, the database client and the example images.

Only these two images contain our code, so only they are built. The database and Adminer use official ready-made images (`postgres:16-alpine` and `adminer`): you don't build them, `docker compose up -d` downloads them automatically in step 1, the first time you start the services. The `upload` service of step 7 reuses the pipeline image.

`--profile batch` includes the pipeline image in the build.

**`.env`: settings and secrets stay out of the code.** `.env` holds the database user, password and name, and your user and group ids (`HOST_UID`, `HOST_GID`: the files written by the pipeline belong to you, not to `root`). `compose.yaml` reads every value from it: no password is written in any file of the repository.

| File | In git? | Holds |
|---|---|---|
| `.env.example` | **yes** | the **names** of the settings, with example values: what the project needs |
| `.env` | **never** (listed in `.gitignore`) | **your** values, including the password |

A password committed to git stays in its history forever, even after you delete it, and anyone who can read the repository can read it. Here `sem` is fine: a database that lives a few hours on your laptop. In a real deployment you would set a strong password in `.env`, and the code wouldn't change at all. If `.env` is missing, Compose stops with `required variable POSTGRES_PASSWORD is missing a value`.

### 0.3 Install kind and kubectl

Skip what you already have (`kind version`, `kubectl version --client`). **kind** creates and deletes the cluster; **kubectl** talks to it. Both are single programs: download, make executable, done. Their versions are fixed on purpose: kind v0.29.0 creates a Kubernetes v1.33.1 cluster, and kubectl v1.33.1 matches it (kubectl supports a cluster at most one minor version away). kind and minikube can live side by side.

```console
$ mkdir -p ~/.local/bin
$ curl -Lo ~/.local/bin/kind https://kind.sigs.k8s.io/dl/v0.29.0/kind-linux-amd64
$ curl -Lo ~/.local/bin/kubectl https://dl.k8s.io/release/v1.33.1/bin/linux/amd64/kubectl
$ chmod +x ~/.local/bin/kind ~/.local/bin/kubectl
$ kind version
kind v0.29.0 go1.24.2 linux/amd64

$ kubectl version --client
Client Version: v1.33.1
Kustomize Version: v5.6.0
```

If `kind version` answers `command not found`, the folder `~/.local/bin` is not in your `PATH` yet (often the case with zsh, or when the folder was just created). Add it, for this terminal and for the next ones:

```console
$ export PATH="$HOME/.local/bin:$PATH"
$ echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc        # with zsh: ~/.zshrc
$ which kind
/home/<you>/.local/bin/kind
```

If you also use **minikube**, stop it during the exercise to save memory (`minikube stop`; `minikube start` brings it back later).

---

## Step 1: start the services

```console
$ docker compose up -d
 ✔ Image postgres:16-alpine             Pulled
 ✔ Image adminer                        Pulled
 ✔ Network sem-pipeline_default         Created
 ✔ Volume sem-pipeline_pgdata           Created
 ✔ Container sem-pipeline-db-1          Started
 ✔ Container sem-pipeline-classifier-1  Started
 ✔ Container sem-pipeline-adminer-1     Started

$ docker compose ps --format "table {{.Service}}\t{{.Status}}"     # about 30 s until the classifier is healthy
SERVICE      STATUS
adminer      Up 42 seconds
classifier   Up 42 seconds (healthy)
db           Up 42 seconds (healthy)
```

The two `Pulled` lines appear only the first time: Docker downloads an official image once, and only if it isn't on your laptop already.

Three containers run and find each other **by name**: inside Compose, the database is `db` and the classifier is `classifier`. The pipeline isn't started yet: it runs once, on request. Plain `docker compose ps` shows all columns, including the ports published on your laptop: Adminer on 8081, the classifier on 3000, the database on 5433. Wait for `(healthy)` on the classifier: it means its model is loaded.

Try the classifier with one image, as in the BentoML exercise:

```console
$ curl -X POST http://localhost:3000/classify -F image=@imgs/1/12_50_vero_09.tif; echo
{"category": "Patterned_surface", "confidence": 0.982, "model": "t0m-R/vit-sem-classification"}
```

---

## Step 2: run the pipeline

```console
$ docker compose run --rm pipeline
 ✔ Container sem-pipeline-db-1         Running
 ✔ Container sem-pipeline-classifier-1 Running
Container sem-pipeline-pipeline-run-xxxxxxxxxxxx Created
4 SEM images in /data/imgs

=== 12_50_vero_09  (/data/imgs/1/12_50_vero_09.tif)
  metadata : 724 keys -> 12_50_vero_09_raw.json, 12_50_vero_09_cleaned.json
  category : Patterned_surface  (confidence 0.982, model t0m-R/vit-sem-classification)
  enriched : 12_50_vero_09_enriched.json
  Variable               Value        Unit
  ---------------------- ------------ ------
  AP_WD                  3.198        mm
  AP_BEAM_TIME           4669.97      Hours
  AP_IMAGE_PIXEL_SIZE    25.09        nm
  AP_HOLDER_HEIGHT       13.700       mm
  AP_BEAM_CURRENT        80.0         µA
  AP_HOLDER_DIAMETER     50.000       mm
  figure   : 12_50_vero_09.png

=== LIL test_defect02  (/data/imgs/2/testdef/LIL test_defect02.tif)
  metadata : 724 keys -> LIL test_defect02_raw.json, LIL test_defect02_cleaned.json
  category : Nanowires  (confidence 0.972, model t0m-R/vit-sem-classification)
  ...
=== protesi_anca1_08  (/data/imgs/3/protesi_anca1_08.tif)
  metadata : 2 keys -> protesi_anca1_08_raw.json, protesi_anca1_08_cleaned.json
  category : Nanowires  (confidence 0.697, model t0m-R/vit-sem-classification)
  ...
  AP_WD                  N/A          N/A
  ...                                      <- the six values are N/A
=== perovskite-inside-010  (/data/imgs/4/perovskite-inside-010.tif)
[ERROR] /data/imgs/4/perovskite-inside-010.tif
  ERROR: not a readable image, or no instrument metadata (tag 34118)

IMAGE                      STATUS  CATEGORY                     CONFIDENCE
12_50_vero_09              OK      Patterned_surface            0.982
LIL test_defect02          OK      Nanowires                    0.972
protesi_anca1_08           OK      Nanowires                    0.697
perovskite-inside-010      ERROR   -                            -

report: /data/output/processing_report.txt
database: 4 images in table 'images'
```

`run` starts the pipeline container once; `--rm` removes it when it ends. It processes every TIFF in `imgs/`.

**The four example images show four real-life cases:**

| Image | Case |
|---|---|
| `12_50_vero_09` | complete metadata (724 keys) |
| `LIL test_defect02` | complete metadata; a space in the name, in a sub-subfolder |
| `protesi_anca1_08` | a valid image with almost no metadata (2 keys): classified, but the table is all N/A |
| `perovskite-inside-010` | not a readable image: recorded as ERROR, and the pipeline goes on |

A real pipeline meets all four. It must not stop at the first bad file, and it must **record** what failed instead of hiding it.

**The six steps for each image** (`pipeline/process.py`):

| # | Step | Done by | Result |
|---|---|---|---|
| 1 | read the instrument tag 34118 of the TIFF | `semmeta` extractor | `<name>_raw.json`, e.g. `"AP_WD": "WD = 3.198 mm"` |
| 2 | keep number and unit | `semmeta` cleaner | `<name>_cleaned.json`, e.g. `"AP_WD": "3.198 mm"` |
| 3 | send the image to `/classify` | the classifier container | category, confidence, model |
| 4 | add the answer to the metadata | `process.py` | **`<name>_enriched.json`** |
| 5 | image + table of the chosen keys | `semmeta` visualizer | **`<name>.png`**, and the table in the terminal |
| 6 | store everything | `db.py` | rows in PostgreSQL |

---

## Step 3: the results

```console
$ ls output
12_50_vero_09_cleaned.json   12_50_vero_09_enriched.json   12_50_vero_09.png   12_50_vero_09_raw.json
LIL test_defect02_cleaned.json   ...   processing_report.txt   ...

$ tail -8 output/12_50_vero_09_enriched.json
  "SV_OPERATOR": "Operator =",
  "classification": {
    "category": "Patterned_surface",
    "confidence": 0.982,
    "model": "t0m-R/vit-sem-classification",
    "classified_at": "2026-11-27T10:15:32+00:00"
  }
}

$ xdg-open output/12_50_vero_09.png        # opens the figure in your image viewer
$ eog output/12_50_vero_09.png             # or: GNOME's image viewer (Eye of GNOME), on Ubuntu
```

The figure opens: the SEM image above, the table of the chosen keys below.

<p align="center"><img src="docs/figure_example.png" width="60%" alt="The figure of 12_50_vero_09: the SEM image of a patterned surface above, and below it the table Extracted Metadata with eight keys, their values and units"></p>

**Two results per image: the enriched JSON and the figure.**

- **`<name>_enriched.json`** is the complete record: all 724 instrument parameters, cleaned, and the AI's answer in its own section `classification`, with the model and the time. Anyone reading the file can tell which values came from the microscope and which from a model.
- **`<name>.png`** is the image with its key parameters, for a person to look at.

The raw and cleaned files are kept on purpose: each stage writes a new file instead of changing the previous one, so you can see what each step did and redo a step without redoing the others.

**Try it: redo only the figure**, with four other keys, from the cleaned file of step 2. No metadata extraction, no classifier, no database (in your `sem-auto` environment):

```console
$ python -c "
import sys; sys.path.insert(0, 'pipeline')
from semmeta import SEMVisualizer
SEMVisualizer('output/12_50_vero_09_cleaned.json', 'imgs/1/12_50_vero_09.tif', output_dir='output/redo',
              variables=['AP_MAG', 'AP_WD', 'AP_PIXEL_SIZE', 'DP_DETECTOR_TYPE']).show_image_with_table()
"
  Variable               Value        Unit
  ---------------------- ------------ ------
  AP_MAG                 14.63        K X
  AP_WD                  3.198        mm
  AP_PIXEL_SIZE          25.09        nm
  DP_DETECTOR_TYPE       InLens

$ eog output/redo/12_50_vero_09.png
```

With 130,000 images, this is the difference between redrawing figures in minutes and running the AI model again on every image.

---

## Step 4: choose your own metadata

The table under each image, and the keys stored as numbers in the database, are by default the six keys of the visualizer:

```text
AP_WD  AP_BEAM_TIME  AP_IMAGE_PIXEL_SIZE  AP_HOLDER_HEIGHT  AP_BEAM_CURRENT  AP_HOLDER_DIAMETER
```

You may want others: the magnification, the detector, the vacuum. There are three ways, from the quickest look to a permanent change.

**4.1 Find the key names.** All metadata of every image is in the database, so you can search it. Use your `sem-auto` environment (step 0.1); `DATABASE_URL` tells `ask.py` where the database is, with the user, password and database name of your `.env` (Compose makes it reachable on port 5433):

```console
$ source ~/venvs/sem-auto/bin/activate
$ export DATABASE_URL=postgresql://sem:sem@localhost:5433/sem
$ python pipeline/ask.py --keys MAG
KEY                                IMAGES
AP_AR_MAG                          2
AP_AR_MAG_FACTOR                   2
...
AP_MAG                             3
...
DP_MAG_CAL                         2
DP_MAG_RANGE                       2
...
SV_MAG_REF_TO                      1

50 keys containing 'MAG'

$ python pipeline/ask.py --keys | tail -1
7xx keys
```

`--keys` (or `--key`, `-k`) followed by a part of a name searches the key names; alone, it lists them all.

**4.2 Ask for any key, for every image, without running the pipeline again:**

```console
$ python pipeline/ask.py AP_MAG AP_WD DP_DETECTOR_TYPE
IMAGE                    CATEGORY               AP_MAG     AP_WD     DP_DETECTOR_TYPE
12_50_vero_09            Patterned_surface      14.63 K X  3.198 mm  Detector = InLens
LIL test_defect02        Nanowires              53.85 K X  3.632 mm  Detector = InLens
protesi_anca1_08         Nanowires              21.59 K X  -         -
```

The same works without the `sem-auto` environment, inside the pipeline container: `docker compose run --rm pipeline python ask.py AP_MAG`.

**4.3 Change the table and the stored keys permanently:** edit `variables.json`, for example add two keys at the end of the list:

```json
  "variables": [
    "AP_WD",
    "AP_BEAM_TIME",
    "AP_IMAGE_PIXEL_SIZE",
    "AP_HOLDER_HEIGHT",
    "AP_BEAM_CURRENT",
    "AP_HOLDER_DIAMETER",
    "AP_MAG",
    "DP_DETECTOR_TYPE"
  ]
```

Then run the pipeline again (no rebuild: Compose gives the container your `variables.json`):

```console
$ docker compose run --rm pipeline        # for each image
  Variable               Value        Unit
  ---------------------- ------------ ------
  AP_WD                  3.198        mm
  ...
  AP_MAG                 14.63        K X
  DP_DETECTOR_TYPE       InLens
```

The figures in `output/` now have eight rows, and the database stores eight keys per image. Text values like `InLens` are kept as text.

---

## Step 5: the database

### Why PostgreSQL, and not Qdrant as in the BentoML exercise?

Qdrant is a **vector** database: it finds similar images through their embeddings. Here there are no embeddings. What we store is **structured data**: per image a category, and parameters with a number and a unit. That is the job of a **relational** database: tables with typed columns, and SQL to ask questions such as "all images with a working distance under 3.5 mm". PostgreSQL is the most widely used open-source one; it also stores whole JSON documents (type `JSONB`), which is how every image keeps all its metadata. In 2019 the same role was played by MySQL.

### Two tables

```text
images                                              selected_metadata
─────────────────────────────────────────           ───────────────────────────────
image (key)    12_50_vero_09                 ──<    image   12_50_vero_09
status         OK                                   key     AP_WD
n_keys         724                                  value   3.198
category       Patterned_surface                    unit    mm
confidence     0.982                                text    (for values that are not numbers)
classifier     t0m-R/vit-sem-classification         one row per key of variables.json
metadata       {all 724 keys + classification}
processed_at   2026-11-27 10:15:32
```

- `images`: one row per image, including failed ones (status ERROR), and in `metadata` the whole enriched JSON.
- `selected_metadata`: the keys of `variables.json` as **numbers**, ready to compare, sort and average.

### Browse it

Open http://localhost:8081 (Adminer) and log in:

| System | Server | Username | Password | Database |
|---|---|---|---|---|
| PostgreSQL | db | sem | sem | sem |

(The user, password and database of your `.env`.)

Click `images` → **Select data**, then `selected_metadata`.

<p align="center"><a href="docs/adminer_images.png"><img src="docs/adminer_images.png" width="100%" alt="Adminer showing the table images: four rows with image, source, status, n_keys, category, confidence, classifier, the metadata JSON and processed_at"></a></p>

The `metadata` column is cut at 100 characters. To read **all the metadata of one image**, including its classification:

- set **Text length** to `0` (no limit) and click **Select**, or click **edit** in front of a row: the whole JSON appears in a text box (just read it, don't save);
- or click **SQL command** (top left), paste one of these queries and click **Execute**:

```sql
-- all 724 keys of one image, as a readable JSON document
SELECT jsonb_pretty(metadata) FROM images WHERE image = '12_50_vero_09';

-- every key and its value as rows: you can sort and filter them
SELECT key, value FROM images, jsonb_each_text(metadata)
 WHERE image = '12_50_vero_09' ORDER BY key;

-- only what the AI model added, for every image
SELECT image,
       metadata->'classification'->>'category'      AS category,
       metadata->'classification'->>'confidence'    AS confidence,
       metadata->'classification'->>'model'         AS model,
       metadata->'classification'->>'classified_at' AS classified_at
  FROM images WHERE status = 'OK' ORDER BY image;
```

`->` reads a part of the JSON as JSON, `->>` reads it as text. The same queries work at the `sem=#` prompt below.

### Query it in SQL

Open a SQL prompt in the database container:

```console
$ docker compose exec db psql -U sem -d sem
```

Then type the queries after the `sem=#` prompt (end each with `;`, leave with `\q`).

**Every image, its status and category:**

```console
sem=# SELECT image, status, n_keys, category, confidence FROM images ORDER BY image;
         image         | status | n_keys |     category      | confidence
-----------------------+--------+--------+-------------------+------------
 12_50_vero_09         | OK     |    724 | Patterned_surface |      0.982
 LIL test_defect02     | OK     |    724 | Nanowires         |      0.972
 perovskite-inside-010 | ERROR  |      0 |                   |
 protesi_anca1_08      | OK     |      2 | Nanowires         |      0.697
(4 rows)
```

**The chosen keys of one image:**

```console
sem=# SELECT key, value, unit, text FROM selected_metadata WHERE image = '12_50_vero_09';
         key         |  value  | unit  |  text
---------------------+---------+-------+--------
 AP_WD               |   3.198 | mm    |
 AP_BEAM_TIME        | 4669.97 | Hours |
 AP_IMAGE_PIXEL_SIZE |   25.09 | nm    |
 AP_HOLDER_HEIGHT    |    13.7 | mm    |
 AP_BEAM_CURRENT     |      80 | µA    |
 AP_HOLDER_DIAMETER  |      50 | mm    |
 AP_MAG              |   14.63 | K X   |
 DP_DETECTOR_TYPE    |         |       | InLens
(8 rows)
```

**A question across both tables** (a JOIN): which images were taken with a working distance under 3.5 mm, and what do they show?

```console
sem=# SELECT i.image, i.category, m.value AS wd_mm
sem-#   FROM images i JOIN selected_metadata m ON m.image = i.image
sem-#  WHERE m.key = 'AP_WD' AND m.value < 3.5;
     image     |     category      | wd_mm
---------------+-------------------+-------
 12_50_vero_09 | Patterned_surface | 3.198
(1 row)
```

**Any key, from the full metadata.** `metadata->>'AP_MAG'` reads a key from the JSON, and the two helper functions `num()` and `unit()` split a value such as `14.63 K X` into a number and a unit:

```console
sem=# SELECT image, num(metadata->>'AP_MAG') AS mag, unit(metadata->>'AP_MAG') AS unit, category
sem-#   FROM images WHERE status = 'OK' ORDER BY mag DESC;
       image       |  mag  | unit |     category
-------------------+-------+------+-------------------
 LIL test_defect02 | 53.85 | K X  | Nanowires
 protesi_anca1_08  | 21.59 | K X  | Nanowires
 12_50_vero_09     | 14.63 | K X  | Patterned_surface
(3 rows)
```

**Run the pipeline twice** (`docker compose run --rm pipeline`): the tables still hold 4 images, not 8. Each image's rows are **replaced**, not added: running again gives the same result.

**Add your own ZEISS TIFFs** to `imgs/` (any subfolder) and run it again: they appear in `output/` and in the database.

### Where is the database?

The database is ordinary files on **your disk**. The container `db` runs the PostgreSQL server; the files live in a Docker **volume**, `sem-pipeline_pgdata`, which Docker mounts into the container:

```text
your disk     /var/lib/docker/volumes/sem-pipeline_pgdata/_data
                  │  mounted into the container db as
                  ▼
container db  /var/lib/postgresql/data              (the same files)
                  │  read and written only by
                  ▼
              the PostgreSQL server, reached by
                ├─ psql      inside the container
                ├─ ask.py    from your laptop, at localhost:5433
                └─ Adminer   in the browser (:8081), at server db
```

From a table to its file on disk:

```console
$ docker compose exec db psql -U sem -d sem -c "SELECT pg_relation_filepath('images');"
 pg_relation_filepath
----------------------
 base/16384/16388
(1 row)

$ docker compose exec db psql -U sem -d sem -c "SELECT oid, datname FROM pg_database WHERE datname = 'sem';"
  oid  | datname
-------+---------
 16384 | sem
(1 row)

$ docker volume inspect sem-pipeline_pgdata --format '{{.Mountpoint}}'
/var/lib/docker/volumes/sem-pipeline_pgdata/_data

$ sudo ls -l /var/lib/docker/volumes/sem-pipeline_pgdata/_data/base/16384/16388
-rw------- 1 70 70 8192 ... 16388
$ docker compose exec db ls -l /var/lib/postgresql/data/base/16384/16388
-rw-------    1 postgres postgres      8192 ... /var/lib/postgresql/data/base/16384/16388
```

- `base/` holds the tables: `16384` is the folder of the database `sem` (its `oid`), `16388` the file of the table `images` (your numbers may differ).
- The last two commands show **one file, seen from two places**: your disk, and the container, through the mount. That's why the data survives `docker compose down`, and goes only with `down -v`.
- The file is **binary**, in 8 kB pages that only the server reads (`sudo strings` on it shows fragments such as your image names). Never edit or delete these files by hand: always go through the server, with `psql`, Adminer or `ask.py`.
- For a readable copy of the whole database, as SQL text: `docker compose exec db pg_dump -U sem -d sem | less`.

---

## Step 6: Kubernetes

Now the same pipeline runs on a Kubernetes cluster. We use **kind** (*Kubernetes in Docker*): a complete small cluster that runs as a container on your laptop.

`k8s.yaml` describes the pipeline in Kubernetes terms:

| In Compose | In Kubernetes (`k8s.yaml`) | Meaning |
|---|---|---|
| service `db` | **Deployment** `db` + **Service** `db` | keep one PostgreSQL running, reachable by the name `db` |
| service `classifier` | **Deployment** `classifier` + **Service** `classifier` | keep the classifier running; no traffic before `/readyz` |
| `docker compose run pipeline` | **Job** `pipeline` | run once until it succeeds, then stop |
| healthcheck | `readinessProbe` / `livenessProbe` | ready for traffic? / alive, or restart it? |
| `.env` | **Secret** `db-credentials` | the database settings, kept apart from the YAML |

The containers find each other by name exactly as in Compose, so the code doesn't change.

**6.1 Create the cluster and give it the images.** The first `kind create` downloads the node image (about 1 GB, a few minutes). The cluster has its **own** image store and can't see the images on your laptop, so `kind load` copies them in (about a minute for the 2 GB classifier). Our two images exist only on your laptop and must be loaded. PostgreSQL could be downloaded by the cluster itself, but on a slow network that takes minutes, so we load it too, and the database starts in seconds.

```console
$ kind create cluster --name sem
Creating cluster "sem" ...
 ✓ Ensuring node image (kindest/node:v1.33.1) 🖼
 ✓ Preparing nodes 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-sem"
You can now use your cluster with:

kubectl cluster-info --context kind-sem

Have a nice day! 👋

$ kubectl config current-context
kind-sem

$ kind load docker-image sem-classifier:1.0 sem-pipeline:1.0 --name sem
Image: "sem-classifier:1.0" with ID "sha256:..." not yet present on node "sem-control-plane", loading...
Image: "sem-pipeline:1.0" with ID "sha256:..." not yet present on node "sem-control-plane", loading...

$ docker pull postgres:16-alpine
$ docker save --platform linux/amd64 postgres:16-alpine -o /tmp/postgres.tar
$ kind load image-archive /tmp/postgres.tar --name sem
$ rm /tmp/postgres.tar

$ docker exec sem-control-plane crictl images | grep -E "postgres|sem-"
docker.io/library/postgres         16-alpine   xxxxxxxxxxxxx   ...
docker.io/library/sem-classifier   1.0         xxxxxxxxxxxxx   ...
docker.io/library/sem-pipeline     1.0         xxxxxxxxxxxxx   ...
```

PostgreSQL is published for many processor types, but your laptop holds only the layers for its own. `docker save --platform linux/amd64` keeps just those, so kind can import them (a plain `kind load docker-image postgres:16-alpine` fails with `content digest ... not found` on recent Docker versions). If `docker save` answers `unknown flag: --platform` (older Docker), use `kind load docker-image postgres:16-alpine --name sem` instead. The last command lists the images now inside the cluster.

kubectl talks to one cluster at a time, its *current context*: `kind create` switched it to `kind-sem`. If you also use minikube, `kubectl config current-context` tells you where you are, and `kubectl config use-context kind-sem` brings you back.

**6.2 A namespace for the pipeline**

A **namespace** is a named space inside the cluster that keeps a group of objects together and apart from the rest. Every cluster starts with a few: `default`, where objects go when nothing else is said, and the `kube-*` ones, where Kubernetes runs its own components. We create one called `sem` and make it the current one, so that every `kubectl` command of the exercise works there without extra options.

```console
$ kubectl get namespaces
NAME                 STATUS   AGE
default              Active   1m
kube-node-lease      Active   1m
kube-public          Active   1m
kube-system          Active   1m
local-path-storage   Active   1m

$ kubectl create namespace sem
namespace/sem created

$ kubectl config set-context --current --namespace=sem
Context "kind-sem" modified.

$ kubectl config view --minify -o jsonpath='{..namespace}'; echo
sem
```

Inside one namespace, pods reach each other by the Service name alone (`db`, `classifier`), exactly as in Docker Compose; from another namespace the full name would be needed, `db.sem.svc.cluster.local`. On a shared cluster, namespaces separate teams, projects or environments (`dev`, `prod`), each with its own quotas and access rights, and `kubectl delete namespace sem` removes everything in it at once. Add `-n <namespace>` to a command to look elsewhere, for example `kubectl get pods -n kube-system`.

**6.3 The database settings, as a Secret**

On Kubernetes, passwords and keys go in a **Secret**: an object that holds them apart from the YAML files. We create it from the same `.env` as Compose:

```console
$ kubectl create secret generic db-credentials --from-env-file=.env
secret/db-credentials created

$ kubectl get secret db-credentials
NAME             TYPE     DATA   AGE
db-credentials   Opaque   5      3s
```

`k8s.yaml` and `k8s-api.yaml` contain no password: each pod reads `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` from the Secret (`secretKeyRef`), and the pipeline builds its `DATABASE_URL` from them. `DATA 5` counts the five settings of `.env`. Strictly, only the password is secret; the user and database name are plain settings, which a real project would put in a **ConfigMap**, the matching object for non-secret configuration. And a Secret is only base64-encoded, not encrypted: on a shared cluster it is protected by access rights (RBAC), or by tools such as Vault or Sealed Secrets.

**6.4 Start everything and watch it**

```console
$ kubectl apply -f k8s.yaml
deployment.apps/db created
service/db created
deployment.apps/classifier created
service/classifier created
job.batch/pipeline created

$ kubectl get pods --watch           # press Ctrl+C when the pipeline pod is Completed
NAME                         READY   STATUS              RESTARTS   AGE
classifier-xxxxxxxxx-xxxxx   0/1     Running             0          11s
db-xxxxxxxxxx-xxxxx          0/1     ContainerCreating   0          11s
pipeline-xxxxx               1/1     Running             0          11s
classifier-xxxxxxxxx-xxxxx   1/1     Running             0          12s
db-xxxxxxxxxx-xxxxx          1/1     Running             0          20s
pipeline-xxxxx               0/1     Completed           0          40s

$ kubectl get pods
NAME                         READY   STATUS      RESTARTS   AGE
classifier-xxxxxxxxx-xxxxx   1/1     Running     0          2m
db-xxxxxxxxxx-xxxxx          1/1     Running     0          2m
pipeline-xxxxx               0/1     Completed   0          2m
```

The pipeline Job shows `0/1 Completed`: its container did its work and exited successfully, so none of its containers runs any more. That is the normal end of a Job (a failed one shows `Error`); the pod is kept so that you can still read its logs.

**If you see an `Error` pod and then a `Completed` one:** a pipeline pod failed, and the Job started a new one (`backoffLimit: 2` in `k8s.yaml` allows two retries). The usual reason is a database that took too long to start. Read both pods' logs, and the events of the database pod:

```console
$ kubectl logs -l job-name=pipeline --tail=3 --prefix
[pod/pipeline-xxxxx/pipeline] report: /data/output/processing_report.txt
[pod/pipeline-xxxxx/pipeline] database: 4 images in table 'images'
[pod/pipeline-yyyyy/pipeline] waiting for the database ...
[pod/pipeline-yyyyy/pipeline] cannot connect to the database at db:5432/sem after x s

$ kubectl describe pod -l app=db | grep -A8 Events
  Normal   Pulling    ...   Pulling image "postgres:16-alpine"
  Normal   Pulled     ...   Successfully pulled image "postgres:16-alpine" in 3m1.2s ...
  Warning  Unhealthy  ...   Readiness probe failed: /run/postgresql:5432 - no response
```

This example comes from a test run without `kind load` for PostgreSQL: its image was downloaded inside the cluster and took 3 minutes (`Pulled ... in 3m1.2s`), longer than the pipeline then waited. That is why step 6.1 loads it, and why the pipeline now waits up to 10 minutes for the database (`DB_WAIT_SECONDS`). A few `Readiness probe failed` lines while PostgreSQL starts are normal. Labels such as `app=db` and `job-name=pipeline` are how you select pods: `kubectl get pods --show-labels` lists them.

**6.5 The results, and your questions**

```console
$ kubectl logs job/pipeline | tail -8
IMAGE                      STATUS  CATEGORY                     CONFIDENCE
12_50_vero_09              OK      Patterned_surface            0.982
LIL test_defect02          OK      Nanowires                    0.972
protesi_anca1_08           OK      Nanowires                    0.697
perovskite-inside-010      ERROR   -                            -

report: /data/output/processing_report.txt
database: 4 images in table 'images'

$ kubectl exec deploy/db -- psql -U sem -d sem -c "SELECT image, status, category, confidence FROM images ORDER BY image;"
         image         | status |     category      | confidence
-----------------------+--------+-------------------+------------
 12_50_vero_09         | OK     | Patterned_surface |      0.982
 LIL test_defect02     | OK     | Nanowires         |      0.972
 perovskite-inside-010 | ERROR  |                   |
 protesi_anca1_08      | OK     | Nanowires         |      0.697
(4 rows)

$ kubectl run query --rm -it --restart=Never --image=sem-pipeline:1.0 --image-pull-policy=Never \
    --env=DATABASE_URL=postgresql://sem:sem@db:5432/sem -- python ask.py AP_MAG AP_WD
IMAGE                    CATEGORY               AP_MAG     AP_WD
12_50_vero_09            Patterned_surface      14.63 K X  3.198 mm
LIL test_defect02        Nanowires              53.85 K X  3.632 mm
protesi_anca1_08         Nanowires              21.59 K X  -
pod "query" deleted from sem namespace
```

The last command starts a one-off pod from the pipeline image, asks the database, and is removed (`--rm`). `query` is the name we give to this pod; after `--` comes the command it runs. `DATABASE_URL` is written out here for clarity, with the values of your `.env`.

**This is the end state of the batch part:** the database and the classifier run as pods, kept alive by Kubernetes; the pipeline ran automatically as a Job; and you can ask the database anything.

The JSON files and figures were written inside the Job's pod: in this short exercise we keep the results in the database. In production, the output folder would be a shared volume.

**Keep the cluster running:** in step 8 you send new images to it. You remove it in step 9.

---

## Step 7: upload an image on a web page

The same pipeline as a web service: upload one TIFF, get back its category and chosen metadata. It's a second BentoML service (`pipeline/api.py`), in the pipeline image.

So far the pipeline ran **in batch**: you start it, it processes a folder, it stops. Now it runs **as a service**: always on, it processes each image as it arrives. That is the behaviour of Nastro's workers, which processed each sequencing file as soon as it appeared in the folder; here the images arrive through HTTP. Both are made of the same `process_image()`: only the way images come in changes.

```console
$ docker compose --profile api up -d upload
```

The page at http://localhost:3001 lists the **three endpoints** of the service (and BentoML's own `/healthz`, `/livez`, `/readyz`, `/metrics`). Each one is used the same way: click it to open it → **Try it out** → fill in the request → **Execute**. The answer appears below, under **Response body**, together with the equivalent `curl` command.

**`POST /process`: send an image.** Next to `image`, **Browse...** and choose a TIFF (from `imgs/`, or one of your own); leave `name` empty to use the file name → **Execute**:

<p align="center"><a href="docs/api_process_try.png"><img src="docs/api_process_try.png" width="80%" alt="The BentoML page of SemPipeline: POST /process opened, a TIFF chosen next to image, the curl command, and the response body with image, source, status, n_keys, category, confidence, classifier and metadata"></a></p>

```json
{
  "image": "12_50_vero_09",
  "source": "/data/output/uploads/12_50_vero_09.tif",
  "status": "OK",
  "n_keys": 724,
  "category": "Patterned_surface",
  "confidence": 0.982,
  "classifier": "t0m-R/vit-sem-classification",
  "metadata": [ {"key": "AP_BEAM_CURRENT", "value": 80.0, "unit": "µA"}, ... ]
}
```

The uploaded file is kept in `output/uploads/`, its JSON files and figure in `output/`, its rows in the database. A JPEG or PNG comes back as `ERROR`: it has no tag 34118.

**`POST /images`: what is in the database.** It needs no input: the request body is just `{}` (already filled in) → **Execute**. The answer lists every image with its status, category, confidence and time, the newest first.

**`POST /ask`: any metadata key, for every image**, like `ask.py`. Replace the request body with the list of keys you want, for example:

```json
{"keys": ["AP_MAG", "AP_WD", "DP_DETECTOR_TYPE"]}
```

→ **Execute**: one entry per image, with its category and the values of these keys (`null` when an image doesn't have the key).

Two services now work in a row: your upload goes to the pipeline service, which calls the classifier service. That's how larger systems are built: small services, each with one job, talking over HTTP.

---

## Step 8: send images to the deployed pipeline through its REST API

Until now the pipeline worked on a folder that you prepared. In real life, new images arrive all the time, from many users and instruments. Here the pipeline deployed on Kubernetes gets a **REST API**: any user, from any computer or script, sends a TIFF with one HTTP request and gets its metadata and category back, while the results land in the same database.

| Idea | In this step |
|---|---|
| **REST API**: resources at URLs, used with standard HTTP methods | `POST /process`, `POST /images`, `POST /ask` on http://localhost:3002 |
| **File upload**: the image travels as `multipart/form-data`, like a web form | `curl -F image=@file.tif`, or `requests.post(..., files=...)` in Python |
| **JSON answer**: easy to read for people and programs | status, category, confidence, the chosen metadata |
| **Self-documented**: BentoML writes the OpenAPI description of the API | the page at http://localhost:3002, and http://localhost:3002/docs.json |

The API is `pipeline/api.py` (the same as in step 7), started from the pipeline image by a Deployment and a Service in `k8s-api.yaml`. It reaches `db` and `classifier` by name, as the Job did.

**8.1 Deploy the API on the cluster of step 6**

```console
$ kubectl apply -f k8s-api.yaml
deployment.apps/upload created
service/upload created

$ kubectl get pods -l app=upload -w        # Ctrl+C when READY is 1/1
NAME                      READY   STATUS    RESTARTS   AGE
upload-xxxxxxxxxx-xxxxx   0/1     Running   0          5s
upload-xxxxxxxxxx-xxxxx   1/1     Running   0          12s
```

**8.2 Open a door from your laptop to the API (terminal 2)**

The Service `upload` lives inside the cluster. `kubectl port-forward` connects port 3002 of your laptop to it; leave it running in a second terminal.

```console
$ kubectl port-forward svc/upload 3002:3001
Forwarding from 127.0.0.1:3002 -> 3001
Forwarding from [::1]:3002 -> 3001
```

Open http://localhost:3002 in the browser: it's the same page as in step 7, with the same three endpoints, now served by Kubernetes.

`port-forward` is a tool for testing from your own laptop: it works only while that terminal stays open, and it always connects to a single pod, even if the API runs as several. On a real cluster, users reach a service through an **Ingress**: a public address such as `https://sem-pipeline.example.org`, with HTTPS and usually a login in front.

**8.3 One user, one image, with curl (terminal 1)**

```console
$ curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3002/readyz
200

$ curl -s -X POST http://localhost:3002/process -F image=@imgs/1/12_50_vero_09.tif -F name=${USER}_vero_09; echo
{"image": "<you>_vero_09", "source": "/data/output/uploads/12_50_vero_09.tif", "status": "OK", "n_keys": 724,
 "category": "Patterned_surface", "confidence": 0.982, "classifier": "t0m-R/vit-sem-classification",
 "metadata": [{"key": "AP_BEAM_CURRENT", "value": 80.0, "unit": "\u00b5A"}, ...]}
```

`/readyz` answers with an **empty body**: only its HTTP status code matters, `200` meaning "ready" (that's what Kubernetes' `readinessProbe` checks, too). `-o /dev/null -w "%{http_code}"` throws the empty body away and prints the code. In the JSON, `\u00b5` is the character µ, written in a form any program can read.

`-F image=@file` sends the file; the optional `-F name=...` stores it under a name of your choice, here your login name (`$USER`, shown as `<you>` below). Without it, the file name is used, and an image sent again replaces its old row.

**8.4 Many users at the same time, from Python**

`push_images.py` sends every TIFF of a folder to `POST /process`, as several users would do at the same time. `--users` is **not** the number of images: it's how many requests are sent **at the same time** (parallel senders). With `--users 4`, four images leave together; with 100 images and `--users 4`, four at a time until all 100 are sent; with `--users 1`, one after the other. Run it from the `sem-auto` environment:

```console
$ source ~/venvs/sem-auto/bin/activate
$ python push_images.py imgs --users 4
4 images -> http://localhost:3002/process, 4 users in parallel

IMAGE                      STATUS  CATEGORY                     CONF.   SECONDS
12_50_vero_09              OK      Patterned_surface            0.982   0.4
LIL test_defect02          OK      Nanowires                    0.972   0.8
protesi_anca1_08           OK      Nanowires                    0.697   1.1
perovskite-inside-010      ERROR   -                            -       1.2

3 OK, 1 ERROR, in 1.2 s
```

The four requests leave at once, but the API processes **one image at a time** (a lock in `api.py` protects its single database connection), so the SECONDS grow from line to line (0.4, 0.8, 1.1, 1.2): each request waits for the ones before it. Try `--users 1` and compare. To serve more users, Kubernetes can run more copies of the API: `kubectl scale deployment upload --replicas=2`. The Service then spreads the requests over the pods; `port-forward`, a tool for testing, always talks to one pod only, so you see the effect with a real entry point (an Ingress), not here.

**8.5 Ask the API what it knows**

```console
$ curl -s -X POST http://localhost:3002/images -H 'Content-Type: application/json' -d '{}' | python -m json.tool
[
    {
        "image": "perovskite-inside-010",
        "status": "ERROR",
        "category": null,
        "confidence": null,
        "processed_at": "2026-11-27T11:31:04+00:00"
    },
    {
        "image": "protesi_anca1_08",
        "status": "OK",
        "category": "Nanowires",
        "confidence": 0.697,
        "processed_at": "2026-11-27T11:31:04+00:00"
    },
    {
        "image": "LIL test_defect02",
        "status": "OK",
        "category": "Nanowires",
        "confidence": 0.972,
        "processed_at": "2026-11-27T11:31:03+00:00"
    },
    {
        "image": "12_50_vero_09",
        "status": "OK",
        "category": "Patterned_surface",
        "confidence": 0.982,
        "processed_at": "2026-11-27T11:31:03+00:00"
    },
    {
        "image": "<you>_vero_09",
        "status": "OK",
        "category": "Patterned_surface",
        "confidence": 0.982,
        "processed_at": "2026-11-27T11:29:37+00:00"
    }
]

$ curl -s -X POST http://localhost:3002/ask -H 'Content-Type: application/json' -d '{"keys": ["AP_MAG", "AP_WD"]}'; echo
[{"image": "12_50_vero_09", "category": "Patterned_surface", "AP_MAG": "14.63 K X", "AP_WD": "3.198 mm"},
 {"image": "LIL test_defect02", "category": "Nanowires", "AP_MAG": "53.85 K X", "AP_WD": "3.632 mm"},
 {"image": "<you>_vero_09", "category": "Patterned_surface", "AP_MAG": "14.63 K X", "AP_WD": "3.198 mm"},
 {"image": "protesi_anca1_08", "category": "Nanowires", "AP_MAG": "21.59 K X", "AP_WD": null}]
```

`python -m json.tool` only lays the JSON out on several lines, to read it. The newest image comes first; `<you>_vero_09`, sent in 8.3, is the oldest. `/ask` lists only the images processed without error.

**8.6 Check in the database**

```console
$ kubectl exec deploy/db -- psql -U sem -d sem -c "SELECT image, status, category, source FROM images ORDER BY image;"
         image         | status |     category      |                     source
-----------------------+--------+-------------------+------------------------------------------------
 12_50_vero_09         | OK     | Patterned_surface | /data/output/uploads/12_50_vero_09.tif
 LIL test_defect02     | OK     | Nanowires         | /data/output/uploads/LIL test_defect02.tif
 <you>_vero_09         | OK     | Patterned_surface | /data/output/uploads/12_50_vero_09.tif
 perovskite-inside-010 | ERROR  |                   | /data/output/uploads/perovskite-inside-010.tif
 protesi_anca1_08      | OK     | Nanowires         | /data/output/uploads/protesi_anca1_08.tif
(5 rows)
```

The `source` column tells you that these rows came through the API, and `<you>_vero_09` is the image you sent under your own name: the same TIFF as `12_50_vero_09`, so the same values. The batch Job of step 6 and the API wrote to the same database: one pipeline, two ways in.

**This is the end state of the exercise:** the database, the classifier and the pipeline's API run as pods on Kubernetes, kept alive and restarted when needed; new images from any user enter through one HTTP request; and everything is queryable in the database.

---

## Step 9: stop

Stop the port-forward with Ctrl+C in terminal 2, then remove the Kubernetes cluster, with all its pods:

```console
$ kind delete cluster --name sem
Deleting cluster "sem" ...
Deleted nodes: ["sem-control-plane"]
```

Then stop the Docker Compose containers (db, classifier, adminer, upload). Choose **one** of the two:

```console
$ docker compose --profile batch --profile api down        # keep the database for next time
 ✔ Container sem-pipeline-upload-1      Removed
 ✔ Container sem-pipeline-adminer-1     Removed
 ✔ Container sem-pipeline-classifier-1  Removed
 ✔ Container sem-pipeline-db-1          Removed
 ✔ Network sem-pipeline_default         Removed

$ docker compose --profile batch --profile api down -v     # or: also delete the database (volume pgdata)
 ...
 ✔ Volume sem-pipeline_pgdata           Removed
```

`docker compose ps` should now list no containers. The images `sem-classifier:1.0` and `sem-pipeline:1.0` stay on your laptop, so nothing needs to be built again:

- **Docker Compose** (steps 1–5): `docker compose up -d` starts the services again in seconds.
- **Kubernetes** (steps 6 and 8): the cluster is gone, so repeat steps 6.1 to 6.3 (cluster and images, namespace, Secret) and apply `k8s.yaml` and `k8s-api.yaml` again.

**When you have finished the exercise**, you can free the disk space used by its images (about 4 GB):

```console
$ docker image rm sem-classifier:1.0 sem-pipeline:1.0 postgres:16-alpine adminer
```

Keep them if you plan to come back: rebuilding takes 10–15 minutes (step 0.2). If another project of yours uses `postgres:16-alpine`, Docker refuses to remove it (`image is being used by running container`): leave it.

---

## Appendix A: if something goes wrong

| Message | What to do |
|---|---|
| the classifier isn't `healthy` after 2 min | `docker compose logs classifier` |
| `waiting for the classifier ...` forever | the classifier isn't running: `docker compose ps` |
| `Permission denied` writing to `output/` | create `output/` and `.env` as in step 0 |
| `ErrImageNeverPull` in Kubernetes | the images weren't loaded: `kind load docker-image ...` (step 6.1) |
| `required variable POSTGRES_PASSWORD is missing a value` | `.env` is missing: `cp .env.example .env` (step 0.2) |
| the pipeline Job shows `Error` | `kubectl logs -l job-name=pipeline --prefix`; often the database started too late (step 6.4) |
| `CreateContainerConfigError` in Kubernetes | the Secret is missing: `kubectl create secret generic db-credentials --from-env-file=.env` (step 6.3) |
| `ask.py` shows other images than the cluster | on your laptop, `ask.py` asks the **Compose** database (port 5433); for the cluster use `kubectl run query ...` (step 6.5) or `POST /ask` (step 8) |
| `kind: command not found` | add `~/.local/bin` to your `PATH` (step 0.3) |
| `kubectl get pods` shows other pods, or none | kubectl talks to another cluster (minikube?): `kubectl config use-context kind-sem` |
| `push_images.py`: `Connection refused` on port 3002 | the port-forward isn't running: start it again in terminal 2 (step 8.2) |
| `port-forward` stops with `lost connection to pod` | the upload pod was restarted: start the port-forward again |
| port 3000, 3001, 3002, 5433 or 8081 already in use | stop the other program, or change the left number in `compose.yaml` (`"3005:3000"`) |

## References

- Burns, B., Grant, B., Oppenheimer, D., Brewer, E., & Wilkes, J. (2016). Borg, Omega, and Kubernetes. *Communications of the ACM*, 59(5), 50–57. https://doi.org/10.1145/2890784
- Dosovitskiy, A., et al. (2021). An image is worth 16×16 words: Transformers for image recognition at scale. *ICLR 2021*. https://openreview.net/forum?id=YicbFdNTTy
- Khalil, A. (2019). *Data Management Tools for NFFA-EUROPE Project*. Master's thesis, Master in High Performance Computing (MHPC), SISSA/ICTP, Trieste. Supervisor: S. Cozzini. The 2019 architecture figure is its Figure 3.5.
- Khalil, A. `semmeta`: SEM metadata extraction, cleaning and visualisation. Python for Data Management I.
- Lusardi, S. *Python for Data Management II*, session 3 (MDMC 2026-27): the BentoML classifier service.
- Rodani, T. `t0m-R/vit-sem-classification`: a ViT-B/32 fine-tuned on SEM images. Hugging Face, Apache-2.0. https://huggingface.co/t0m-R/vit-sem-classification
- Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures* (REST, chapter 5). PhD thesis, University of California, Irvine.
- Wilkinson, M. D., et al. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data*, 3, 160018. https://doi.org/10.1038/sdata.2016.18
- Docker and Kubernetes logos: trademarks of Docker, Inc. and of The Linux Foundation, used only to name the tools.
