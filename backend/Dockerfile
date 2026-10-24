FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm || true
# Optional real embeddings: build with --build-arg ML=1
ARG ML=0
RUN if [ "$ML" = "1" ]; then pip install --no-cache-dir -r requirements-ml.txt; fi
COPY app ./app
COPY fixtures ./fixtures
ENV HEALTHDOC_DATA_DIR=/data
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
