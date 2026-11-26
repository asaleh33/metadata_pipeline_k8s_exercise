# The BentoML classifier, with its model inside the image (works offline, also in Kubernetes).
# service.py is the course solution, unchanged.
FROM python:3.12-slim

# torch in its CPU version (the default one adds about 5 GB of GPU libraries), then BentoML and transformers
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir "bentoml>=1.4" "transformers>=4.40" "pillow>=10"

# Download the model once, at build time, into the image
ENV HF_HOME=/opt/huggingface
RUN python -c "from transformers import AutoImageProcessor, AutoModelForImageClassification as M; \
m = 't0m-R/vit-sem-classification'; AutoImageProcessor.from_pretrained(m); M.from_pretrained(m)"
# From now on, never contact Hugging Face: use the copy above
ENV HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1

WORKDIR /app
COPY service.py .
EXPOSE 3000
CMD ["bentoml", "serve", "service:SemClassifier", "--port", "3000"]
