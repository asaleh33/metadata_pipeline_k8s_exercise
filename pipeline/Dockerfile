# The pipeline: semmeta + the chain (process.py) + the database client.
# Build from the exercise folder:  docker build -f pipeline/Dockerfile -t sem-pipeline:1.0 .
FROM python:3.12-slim

WORKDIR /app
COPY pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ /app/
# The keys shown in the table and stored (Compose mounts ./variables.json over it: edit without rebuilding)
COPY variables.json /app/variables.json
# The example images travel inside the image (needed in Kubernetes; Compose mounts ./imgs over them)
COPY imgs/ /data/imgs/
RUN mkdir -p /data/output && chmod 777 /data/output && ln -s /data/imgs /app/imgs

ENV INPUT_DIR=/data/imgs OUTPUT_DIR=/data/output \
    HOME=/tmp MPLCONFIGDIR=/tmp/matplotlib PYTHONUNBUFFERED=1
CMD ["python", "run_batch.py"]
