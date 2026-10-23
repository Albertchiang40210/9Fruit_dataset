FROM python:3.12-slim

# 以 --build-arg REQUIREMENTS=requirements-web.txt 可建置不含 YOLO/torch 的輕量前端映像檔
ARG REQUIREMENTS=requirements-api.txt

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libxcb1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY ${REQUIREMENTS} ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
# 模型權重（不在 git 中）：請放在 result/ 並透過 compose volume 掛載，或自行 COPY
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "live_predict_api:app", "--host", "0.0.0.0", "--port", "8000"]
