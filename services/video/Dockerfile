# CBAG video service — talking-head generation.
# Build context is the repo root (see docker-compose.yml). This scaffold is light
# (FastAPI only); the chosen modern backend + weights are added once the spike
# confirms what builds on Blackwell (aarch64 + CUDA 13). SadTalker (2023) is not
# used. Heavy backends will switch this base to an NGC PyTorch aarch64 image.
ARG CBAG_CUDA_BASE=nvidia/cuda:13.0.1-base-ubuntu24.04
FROM ${CBAG_CUDA_BASE}

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY services/video/requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY services/video/storage.py ./storage.py
COPY services/video/comfyui_sonic.py ./comfyui_sonic.py
COPY services/video/comfyui_clone.py ./comfyui_clone.py
COPY services/video/app.py ./app.py
COPY services/video/default_faces ./default_faces

ENV SERVICE_NAME=video ARTIFACT_ROOT=/artifacts DEFAULT_FACES_DIR=/app/default_faces
EXPOSE 8200
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8200"]
