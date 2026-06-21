# CBAG ComfyUI engine — the video backend host (Blackwell-ready).
#
# Uses a stock, self-consistent torch+torchvision+torchaudio stack from the
# PyTorch cu130 index (all ABI-matched). Verified on the GB10: a CUDA matmul runs
# and torch reports "NVIDIA GB10" (sm_121). This avoids the NGC container's
# bespoke-ABI torchaudio mismatch (no PyPI torchaudio loads against NGC's torch).
# ComfyUI absorbs the rest; our `video` service drives it over the HTTP API.
FROM nvidia/cuda:13.0.1-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip git ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Blackwell-capable torch stack (matched trio from the cu130 index).
RUN pip install --no-cache-dir --break-system-packages \
      torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

WORKDIR /opt
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git
WORKDIR /opt/ComfyUI
# Keep our cu130 torch stack: strip torch* from ComfyUI's requirements so pip
# does not replace them; install everything else against it.
RUN sed -i -E '/^torch([=<>!~; ]|$)/Id; /^torchvision([=<>!~; ]|$)/Id; /^torchaudio([=<>!~; ]|$)/Id' requirements.txt \
 && pip install --no-cache-dir --break-system-packages -r requirements.txt

# Sonic talking-head node (audio + portrait -> video). Keep our cu130 torch stack.
RUN git clone --depth 1 https://github.com/smthemex/ComfyUI_Sonic.git custom_nodes/ComfyUI_Sonic \
 && sed -i -E '/^torch([=<>!~; ]|$)/Id; /^torchvision([=<>!~; ]|$)/Id; /^torchaudio([=<>!~; ]|$)/Id' custom_nodes/ComfyUI_Sonic/requirements.txt \
 && pip install --no-cache-dir --break-system-packages -r custom_nodes/ComfyUI_Sonic/requirements.txt

# Qwen3-TTS voice-clone node (reference audio + text -> cloned speech). Weights
# auto-download to models/TTS/Qwen3-TTS on first use. Keep our cu130 torch stack.
RUN git clone --depth 1 https://github.com/1038lab/ComfyUI-QwenTTS.git custom_nodes/ComfyUI-QwenTTS \
 && sed -i -E '/^torch([=<>!~; ]|$)/Id; /^torchvision([=<>!~; ]|$)/Id; /^torchaudio([=<>!~; ]|$)/Id' custom_nodes/ComfyUI-QwenTTS/requirements.txt \
 && pip install --no-cache-dir --break-system-packages -r custom_nodes/ComfyUI-QwenTTS/requirements.txt
# The node imports qwen_tts but forgets it in requirements; it pins transformers==4.57.3.
RUN pip install --no-cache-dir --break-system-packages qwen-tts

EXPOSE 8188
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
