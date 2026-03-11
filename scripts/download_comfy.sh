#!/bin/bash
# download_comfy.sh — Descarga de modelos para ComfyUI al host
#
# Este script corre en el HOST, no dentro de ningún contenedor.
# Descarga modelos directamente al volumen de ComfyUI (COMFY_PATH).
#
# Los modelos de Ollama NO se gestionan aquí — Ollama corre dentro del
# contenedor y accede a su propio volumen (ollama_data). Para descargar
# modelos Ollama usar:
#
#   just setup-models
#
# Uso:
#   bash scripts/download_comfy.sh
#   COMFY_PATH=/ruta/custom bash scripts/download_comfy.sh
#
# Ejecutar desde la raíz del proyecto.

set -e

echo "🔽 Descargando modelos ComfyUI..."

# ─────────────────────────────────────────────
# Función auxiliar: descarga si no existe
# ─────────────────────────────────────────────
download() {
    local url="$1"
    local dest="$2"

    if [ -f "$dest" ]; then
        echo "✅ Ya existe: $dest"
    else
        echo "⬇️  Descargando: $(basename "$dest")"
        mkdir -p "$(dirname "$dest")"
        wget -c "$url" -O "$dest"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Flujo: assets/ComfyUI/comic.json
#
# Pipeline: IPAdapter estilo cómic + ControlNet Canny SDXL + ControlNet Depth SDXL
# Checkpoint base: JuggernautXL Ragnarok (SDXL)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━ comic.json ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Checkpoint (nodo 3: CheckpointLoaderSimple) ───────────────────────────────
# ckpt_name: "juggernautXL_ragnarokBy.safetensors"
# NOTA: el nombre del archivo descargado debe coincidir exactamente con
#       ckpt_name en el JSON. Si el repo cambia el nombre, ajustar aquí
#       o editar el workflow en ComfyUI.
# Alternativa con nombre exacto (puede requerir cuenta CivitAI):
#   https://civitai.com/api/download/models/288982
download \
    "https://huggingface.co/RunDiffusion/Juggernaut-XL-Lightning/blob/main/Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors" \
    "${COMFY_PATH:-./comfy}/models/checkpoints/juggernautXL_ragnarokBy.safetensors"

# ── ControlNet Canny SDXL (nodo 20: ControlNetLoader) ────────────────────────
# control_net_name: "canny-sdxl-fp16.safetensors"
download \
    "https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model_V2.safetensors" \
    "${COMFY_PATH:-./comfy}/models/controlnet/canny-sdxl-fp16.safetensors"

# ── ControlNet Depth SDXL (nodo 27: ControlNetLoader) ────────────────────────
# control_net_name: "depth-sdxl-fp16.safetensors"
download \
    "https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors" \
    "${COMFY_PATH:-./comfy}/models/controlnet/depth-sdxl-fp16.safetensors"

# ── IPAdapter PLUS FACE SDXL (nodo 14: IPAdapterUnifiedLoader) ───────────────
# preset: "PLUS FACE (portraits)" → ip-adapter-plus-face_sdxl_vit-h
download \
    "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors" \
    "${COMFY_PATH:-./comfy}/models/ipadapter/ip-adapter-plus-face_sdxl_vit-h.safetensors"

# ── CLIPVision ViT-H-14 (requerido por IPAdapter SDXL ViT-H) ─────────────────
# El preset SDXL PLUS usa ViT-H-14, no ViT-L-14.
# Ruta esperada por IPAdapterUnifiedLoader: models/clip_vision/
download \
    "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors" \
    "${COMFY_PATH:-./comfy}/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"

# ── Depth Anything V2 ViT-L (nodo 24: DepthAnythingV2Preprocessor) ───────────
# ckpt_name: "depth_anything_v2_vitl.pth"
# Requiere el custom node comfyui_controlnet_aux (o similar) instalado en ComfyUI.
download \
    "https://huggingface.co/depth-anything/Depth-Anything-V2-Large/resolve/main/depth_anything_v2_vitl.pth" \
    "${COMFY_PATH:-./comfy}/models/checkpoints/depth_anything_v2_vitl.pth"

echo ""
echo "✅ Modelos comic.json descargados en: ${COMFY_PATH:-./comfy}/models/"

# ─────────────────────────────────────────────────────────────────────────────
# Modelos adicionales (SD 1.x / SDXL genéricos — no usados por comic.json)
# Descomenta los que necesites para otros flujos.
# ─────────────────────────────────────────────────────────────────────────────

# SDXL base y refiner (Stability AI)
# download "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" "${COMFY_PATH:-./comfy}/models/checkpoints/sd_xl_base_1.0.safetensors"
# download "https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors" "${COMFY_PATH:-./comfy}/models/checkpoints/sd_xl_refiner_1.0.safetensors"

# VAE MSE (SD 1.x)
# download "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors" "${COMFY_PATH:-./comfy}/models/vae/vae-ft-mse-840000-ema-pruned.safetensors"

# CLIPVision ViT-L (IPAdapter SD 1.x — distinto del ViT-H usado en SDXL)
# download "https://huggingface.co/openai/clip-vit-large-patch14/resolve/main/pytorch_model.bin" "${COMFY_PATH:-./comfy}/models/clip_vision/clip_vit14.bin"

# Upscalers ESRGAN
# download "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth" "${COMFY_PATH:-./comfy}/models/upscale_models/RealESRGAN_x4plus.pth"
# download "https://huggingface.co/sberbank-ai/Real-ESRGAN/resolve/main/RealESRGAN_x4.pth" "${COMFY_PATH:-./comfy}/models/upscale_models/RealESRGAN_x4.pth"
