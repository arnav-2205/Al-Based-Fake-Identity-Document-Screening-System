# SIH26188 — System Inspection Report

**Generated:** 2026-09-02T00:55 IST  
**Inspector:** ML Automation Agent  

---

## 1. Operating System

| Field | Value |
|---|---|
| OS | Microsoft Windows 11 Home Single Language |
| Version | 10.0.26200 Build 26200 |
| Architecture | x64-based PC |

---

## 2. CPU

| Field | Value |
|---|---|
| Model | 12th Gen Intel Core i5-12450H |
| Cores | 8 physical, 12 logical |
| Architecture | Alder Lake (P-core + E-core hybrid) |

**Assessment:** Good for ML training with moderate-sized models. The 12 logical processors allow efficient data-loading parallelism.

---

## 3. RAM

| Field | Value |
|---|---|
| Total Physical Memory | 16,025 MB (~16 GB) |

**Assessment:** Sufficient for training EfficientNet-B0/ResNet50 with moderate batch sizes. Must monitor usage during training to avoid swapping. Large datasets should be loaded lazily (PyTorch DataLoader).

---

## 4. GPU

| Field | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 2050 |
| VRAM | 4096 MiB (4 GB) |
| Driver | NVIDIA 592.82 |
| CUDA (Driver) | 13.1 |
| Temperature | 56°C idle |
| Power | 9W / 31W cap |
| Current Usage | 8 MiB / 4096 MiB |

**Assessment:** GPU is available with 4 GB VRAM. This is usable for training with constraints:
- EfficientNet-B0 at 224×224: batch size 16–32
- ResNet50 at 224×224: batch size 8–16
- Must use mixed precision (AMP) to stretch VRAM
- Gradient accumulation for effective larger batches

---

## 5. PyTorch & CUDA

| Field | Value |
|---|---|
| PyTorch Version | 2.10.0+cpu |
| CUDA Available (PyTorch) | **FALSE** |
| Installed Variant | **CPU-only build** |

> [!CAUTION]
> **PyTorch is installed as CPU-only but a CUDA-capable GPU exists.** This must be fixed before training. The current `torch` (2.10.0+cpu) must be replaced with the CUDA 12.x build to utilise the RTX 2050.

**Action Required:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

---

## 6. Python Environment

| Field | Value |
|---|---|
| Python | 3.14.2 |
| pip | 26.0.1 |
| Location | `C:\Users\swami\AppData\Local\Python\pythoncore-3.14-64` |
| Virtual Env | Global install (no venv detected in project) |

> [!WARNING]
> Python 3.14 is very new. Some ML packages (PaddleOCR, InsightFace, dlib) may not yet support Python 3.14. We may need a Python 3.11 or 3.12 venv.

---

## 7. Installed ML Packages

| Package | Version | Status |
|---|---|---|
| torch | 2.10.0 (CPU) | ⚠️ Needs CUDA build |
| torchvision | 0.25.0 | ⚠️ Needs CUDA build |
| opencv-python | 4.13.0.92 | ✅ |
| pillow | 12.1.1 | ✅ |
| numpy | 2.4.3 | ✅ |
| pandas | 2.3.3 | ✅ |
| scikit-learn | 1.8.0 | ✅ |
| scikit-image | 0.26.0 | ✅ |
| scipy | 1.17.1 | ✅ |
| timm | 1.0.25 | ✅ |
| facenet-pytorch | 2.6.0 | ✅ |
| fastapi | 0.135.2 | ✅ |
| uvicorn | 0.42.0 | ✅ |

**Not Installed (needed):**
| Package | Purpose |
|---|---|
| paddleocr | OCR engine |
| paddlepaddle | PaddleOCR backend |
| insightface | Face embeddings (ArcFace) |
| onnxruntime | ONNX model inference |
| albumentations | Training augmentations |
| PyYAML | Config files |

---

## 8. Disk Space

| Drive | Used | Free | Total |
|---|---|---|---|
| C: | 292.84 GB | **182.84 GB** | 475.68 GB |

**Assessment:** 182 GB free is excellent. The 8–15 GB dataset budget is well within capacity.

---

## 9. Existing Project Structure

The project at `C:\Users\swami\Desktop\SIH26188` has an existing `ai-service/` with:

### Already Implemented (Stub/Partial)
| Component | File | Status |
|---|---|---|
| OCR/MRZ router | `ai-service/app/routers/ocr.py` | Stub with PaddleOCR hook |
| Tamper router | `ai-service/app/routers/tamper.py` | Stub |
| Face router | `ai-service/app/routers/face.py` | Stub |
| OCR engine | `ai-service/app/services/ocr_engine.py` | PaddleOCR integration (stubbed) |
| MRZ parser | `ai-service/app/services/mrz.py` | ✅ **Real ICAO 9303 TD3 parser with checksum** |
| ELA | `ai-service/app/services/ela.py` | ✅ **Real ELA implementation** |
| EXIF checker | `ai-service/app/services/exif_check.py` | ✅ **Real EXIF analysis** |
| Tamper model | `ai-service/app/services/tamper_model.py` | EfficientNet-B0 skeleton (no weights) |
| Face engine | `ai-service/app/services/face_engine.py` | InsightFace hook (stub embeddings) |
| Config | `ai-service/app/config.py` | `AI_USE_REAL_MODELS` toggle |
| Schemas | `ai-service/app/schemas.py` | Pydantic models for OCR/Tamper/Face |

### Key Observations
1. The `tamper_model.py` defines EfficientNet-B0 with 2-class output but has **no trained weights** (TODO comment).
2. The `face_engine.py` has InsightFace ArcFace integration ready, just needs the model downloaded.
3. The `mrz.py` has a **complete, working TD3 parser** with check-digit validation.
4. The `ela.py` provides **real ELA** (Error Level Analysis) with heatmap generation.
5. The `exif_check.py` provides **real EXIF metadata analysis**.

---

## 10. Existing Datasets

| Location | Status |
|---|---|
| `C:\Users\vv\data\midv500\01_alb_id.zip` | **NOT FOUND** (different user path) |
| Project `ml/` directory | Empty (just created) |
| Any `.pt`, `.pth`, `.onnx` model files | **NONE found** |

---

## 11. Summary & Critical Actions

| # | Action | Priority |
|---|---|---|
| 1 | Replace PyTorch CPU with CUDA build | 🔴 Critical |
| 2 | Verify Python 3.14 compatibility with PaddleOCR/InsightFace | 🔴 Critical |
| 3 | Consider Python 3.11/3.12 venv if compatibility fails | 🟡 High |
| 4 | Install albumentations, PyYAML, onnxruntime | 🟡 High |
| 5 | Download MIDV-500 dataset (~1 GB) | 🟢 Normal |
| 6 | Download DocTamper subset (~2-3 GB) | 🟢 Normal |
| 7 | Download stamp dataset (~0.5 GB) | 🟢 Normal |
| 8 | Train EfficientNet-B0 tampering model | 🟢 Normal |

### Hardware Viability Matrix

| Model | Trainable on this machine? | Strategy |
|---|---|---|
| EfficientNet-B0 (tampering) | ✅ Yes | AMP, batch 16, 224×224 |
| ResNet50 (backup) | ✅ Yes | AMP, batch 8, 224×224 |
| PaddleOCR (inference) | ✅ Yes | Pretrained, no training needed |
| InsightFace (face) | ✅ Yes | Pretrained, no training needed |
| Anti-spoofing (liveness) | ✅ Yes | Fine-tune small model |
| ResNet18 (stamp) | ✅ Yes | AMP, batch 32, 224×224 |
