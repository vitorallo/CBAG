# CBAG TTS service — default voices via Kokoro (ONNX).
# Build context is the repo root (see docker-compose.yml). The model is baked
# into the image so the container needs no network at runtime. Voice cloning
# (advanced) is added later with a heavier engine.
ARG CBAG_CUDA_BASE=nvidia/cuda:13.0.1-base-ubuntu24.04
FROM ${CBAG_CUDA_BASE}

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-pip espeak-ng libsndfile1 wget ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip3 install --no-cache-dir --break-system-packages \
      fastapi "uvicorn[standard]" soundfile numpy kokoro-onnx onnxruntime

# Bake in the Kokoro model + voices (self-contained, offline at runtime).
RUN mkdir -p /models \
 && wget -q -O /models/kokoro-v1.0.onnx \
      https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx \
 && wget -q -O /models/voices-v1.0.bin \
      https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

COPY services/tts/voices.py ./voices.py
COPY services/tts/storage.py ./storage.py
COPY services/tts/app.py ./app.py

ENV SERVICE_NAME=tts \
    KOKORO_MODEL=/models/kokoro-v1.0.onnx \
    KOKORO_VOICES=/models/voices-v1.0.bin
EXPOSE 8100
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
