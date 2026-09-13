# SIH26188 — ML Training Plan

**Generated:** 2026-09-02T00:56 IST  
**Hardware:** Intel i5-12450H · 16 GB RAM · RTX 2050 (4 GB VRAM) · 182 GB free  
**Python:** 3.14.2 · PyTorch 2.10.0 (CPU → must upgrade to CUDA)  

---

## Execution Order

| Phase | Component | Approach | Est. Time |
|---|---|---|---|
| 0 | Environment Setup | Install CUDA PyTorch, check compatibility | 30 min |
| 1 | Dataset Acquisition | Download datasets within 8–12 GB budget | 1–2 hrs |
| 2 | Dataset Inventory | Catalog, validate, manifest generation | 1 hr |
| 3 | Document/OCR Pipeline | PaddleOCR pretrained + field extraction | 2 hrs |
| 4 | MRZ Pipeline | Extend existing parser + MRZ OCR | 1 hr |
| 5 | Tampering Detection | Train EfficientNet-B0 on DocTamper + MIDV | 4–6 hrs |
| 6 | Stamp Verification | Train ResNet18 on StaVer | 2–3 hrs |
| 7 | Face Verification | InsightFace ArcFace pretrained | 1 hr |
| 8 | Liveness / Anti-Spoofing | Fine-tune on CelebA-Spoof subset | 2–3 hrs |
| 9 | Risk Engine | Weighted rule-based scoring | 1 hr |
| 10 | Unified Pipeline | End-to-end inference pipeline | 2 hrs |
| 11 | FastAPI Integration | Model service endpoints | 2 hrs |
| 12 | Final Evaluation | Metrics, reports, exports | 2 hrs |

---

## Phase 0 — Environment Setup

### 0.1 PyTorch CUDA Installation

```bash
pip uninstall torch torchvision -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

**Verify:**
```python
import torch
assert torch.cuda.is_available()
print(torch.cuda.get_device_name(0))  # → NVIDIA GeForce RTX 2050
```

### 0.2 Additional Dependencies

```bash
pip install albumentations pyyaml tqdm matplotlib seaborn
pip install onnxruntime-gpu  # or onnxruntime for CPU fallback
```

### 0.3 PaddleOCR Compatibility Check

PaddleOCR may not support Python 3.14. If it fails:
- Option A: Use `easyocr` as alternative
- Option B: Create a Python 3.11 venv specifically for OCR
- Option C: Use `paddleocr` via subprocess with a compatible Python

### 0.4 Virtual Environment

```bash
python -m venv ml/.venv
ml/.venv/Scripts/activate
pip install -r ml/requirements-ml.txt
```

---

## Phase 1 — Dataset Strategy

### Budget Allocation

| Dataset | Purpose | Est. Size | Models |
|---|---|---|---|
| MIDV-500 | Document images (passport, ID, DL) | ~1.0 GB | OCR, Doc classification, Tampering |
| DocTamper (subset) | Text/photo tampering with masks | ~2.5 GB | Tampering detection |
| StaVer | Stamp genuine vs. forged | ~0.5 GB | Stamp verification |
| Indian Passports (synthetic) | Indian domain adaptation | ~0.3 GB | OCR, Indian fine-tuning |
| Indian DL (synthetic) | Indian driving licence OCR | ~0.2 GB | OCR, Indian fine-tuning |
| MRZ test data | MRZ OCR/parsing validation | ~0.05 GB | MRZ validation |
| CelebA-Spoof (subset) | Anti-spoofing training | ~2.0 GB | Liveness detection |
| Synthetic tampering (generated) | Augmented tampering pairs | ~1.0 GB | Tampering |
| **TOTAL** | | **~7.5 GB** | |

> [!IMPORTANT]
> Budget: 8–12 GB target, 15 GB hard max. The ~7.5 GB estimate leaves headroom for additional data or model checkpoints.

### Download Priority

1. MIDV-500 (core document dataset)
2. DocTamper (core tampering dataset)
3. StaVer (stamp dataset)
4. Indian synthetic datasets (HuggingFace)
5. CelebA-Spoof subset (anti-spoofing)
6. MRZ test samples (GitHub repos)

---

## Phase 2 — Dataset Inventory

Create `ml/datasets/inventory.csv` with columns:
```
dataset_name,source,license,document_type,language,image_count,annotation_count,size_bytes,status,purpose
```

Create `ml/datasets/DATASET_REPORT.md` documenting each dataset.

---

## Phase 3 — Document / OCR Pipeline (MODEL 1–2)

### Architecture

```
INPUT IMAGE
    ↓
Document Detection (pretrained object detector or heuristic)
    ↓
Perspective Correction (OpenCV 4-point warp)
    ↓
Image Enhancement (CLAHE + denoising)
    ↓
OCR (PaddleOCR PP-OCRv4 or EasyOCR)
    ↓
Field Extraction (regex patterns per document type)
    ↓
Field Normalization (date formats, name casing)
    ↓
Validation (rule engine)
```

### Strategy
- **DO NOT** train OCR from scratch
- Use PaddleOCR pretrained model (PP-OCRv4, English)
- Fine-tune on MIDV-500 text crops if accuracy is insufficient
- Add document-type-specific field extraction patterns
- Indian language support: PaddleOCR supports Hindi/Devanagari

### Config: `ml/config/ocr.yaml`
```yaml
framework: paddleocr
model: PP-OCRv4
language: en
use_angle_cls: true
det_model: ch_PP-OCRv4_det
rec_model: en_PP-OCRv4_rec
image_size: [640, 640]
confidence_threshold: 0.7
```

### Fields to Extract

| Document Type | Fields |
|---|---|
| Passport | Name, Passport Number, Nationality, DOB, Expiry, Gender |
| Visa | Visa Number, Type, Entry Date, Stay Duration |
| National ID | Name, ID Number, DOB, Address |
| Driving Licence | Name, DL Number, DOB, Expiry, Class |
| Permit | Permit Number, Type, Validity |

---

## Phase 4 — MRZ Pipeline (MODEL 3)

### Architecture

```
INPUT IMAGE
    ↓
MRZ Region Detection (existing regex + optional YOLO-tiny detector)
    ↓
MRZ OCR (PaddleOCR on MRZ crop)
    ↓
MRZ Parser (existing ICAO 9303 parser → extend to TD1/TD2)
    ↓
Checksum Validation (already implemented)
    ↓
Cross-Zone Comparison (MRZ fields vs. VIZ fields)
```

### Strategy
- **MRZ parser already exists** in `ai-service/app/services/mrz.py` (TD3 complete)
- Extend to support TD1 (3×30 chars) and TD2 (2×36 chars)
- MRZ OCR: use PaddleOCR on the cropped MRZ region
- MRZ detection: use regex on OCR output + optional region detector
- Use tesseractMRZ and mrz-reader GitHub repos for test data

### Config: `ml/config/mrz.yaml`
```yaml
td1_line_length: 30
td1_num_lines: 3
td2_line_length: 36
td2_num_lines: 2
td3_line_length: 44
td3_num_lines: 2
char_set: "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
```

---

## Phase 5 — Tampering Detection (MODEL 4–6)

### Architecture: Binary → Multi-Class

**Stage 1: Binary Classification**
```
INPUT IMAGE → Preprocessing → EfficientNet-B0 → [Genuine, Tampered]
```

**Stage 2: Multi-Class (after binary works)**
```
INPUT IMAGE → Preprocessing → EfficientNet-B0 → [Genuine, Photo, Text, Stamp, Other]
```

### Model Selection

| Model | Params | VRAM (batch 16) | Accuracy (est.) |
|---|---|---|---|
| EfficientNet-B0 | 5.3M | ~1.5 GB | Good |
| EfficientNet-B2 | 9.2M | ~2.2 GB | Better |
| ResNet50 | 25.6M | ~2.5 GB | Good |

**Primary choice:** EfficientNet-B0 (best accuracy/VRAM trade-off for 4 GB)

### Training Configuration: `ml/config/tampering.yaml`

```yaml
# Dataset
dataset_path: ml/datasets/tampering/
image_size: 224
num_classes: 2  # Phase 1: binary

# Training
batch_size: 16
epochs: 20
learning_rate: 0.001
optimizer: AdamW
weight_decay: 0.01
scheduler: CosineAnnealingLR
warmup_epochs: 2

# Augmentation
augmentation:
  - HorizontalFlip(p=0.3)
  - RandomBrightnessContrast(p=0.3)
  - GaussianBlur(p=0.2)
  - JPEGCompression(quality_lower=70, quality_upper=100, p=0.3)
  - ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=5, p=0.3)

# Hardware
mixed_precision: true
gradient_accumulation_steps: 2
num_workers: 4
pin_memory: true

# Checkpointing
checkpoint_dir: ml/checkpoints/tampering/
save_best: true
save_last: true
early_stopping_patience: 5

# Reproducibility
seed: 42
```

### Training Pipeline

```
1. Load DocTamper + MIDV-500 genuine images
2. Create genuine/tampered splits
3. Apply augmentations (training only)
4. Transfer learning: ImageNet pretrained → freeze backbone (epoch 0-5)
5. Unfreeze backbone → fine-tune all layers (epoch 5-20)
6. Early stopping on val_loss
7. Save best_model.pt and last_model.pt
```

### Evaluation Metrics
- Accuracy, Precision, Recall, F1-Score
- ROC-AUC
- False Positive Rate (FPR)
- **False Negative Rate (FNR)** ← critical for security
- Confusion matrix visualization
- ROC curve visualization

### Localization (Phase 2)
If DocTamper provides pixel-level masks:
- Add a segmentation head (U-Net style decoder on EfficientNet encoder)
- Output: tampering probability + heatmap
- Combined with ELA heatmap for multi-signal visualization

---

## Phase 6 — Stamp Verification (MODEL 7)

### Architecture

```
INPUT IMAGE → Stamp Region Detection → Stamp Crop → ResNet18 → [Genuine, Forged]
```

### Training Configuration: `ml/config/stamp.yaml`

```yaml
model: resnet18
pretrained: imagenet
num_classes: 2
image_size: 128
batch_size: 32
epochs: 15
learning_rate: 0.0005
optimizer: Adam
mixed_precision: true
seed: 42
```

### Strategy
- Use StaVer dataset for genuine/forged stamp classification
- ResNet18 is sufficient for binary stamp classification (small, fast)
- Stamp region detection: heuristic (bottom-right quadrant) → later replace with actual detector
- Output: `stamp_tampering_score` [0.0, 1.0]

---

## Phase 7 — Face Verification (MODEL 8)

### Architecture

```
Document Portrait → Face Detection → Alignment → ArcFace Embedding (512-D)
                                                                    ↓
Live Photo → Face Detection → Alignment → ArcFace Embedding (512-D)
                                                                    ↓
                                                    Cosine Similarity → Match/Mismatch
```

### Strategy
- **DO NOT** train face recognition from scratch
- Use InsightFace ArcFace `buffalo_l` (pretrained, 512-D embeddings)
- Already scaffolded in `ai-service/app/services/face_engine.py`
- Alternative: `facenet-pytorch` (already installed, InceptionResnetV1)
- Determine threshold using validation pairs

### Config: `ml/config/face.yaml`

```yaml
framework: insightface  # or facenet-pytorch
model: buffalo_l
embedding_dim: 512
det_size: [640, 640]
similarity_metric: cosine
match_threshold: 0.55  # to be optimized on validation data
```

### Evaluation Metrics
- FAR (False Accept Rate) at various thresholds
- FRR (False Reject Rate)
- TAR @ FAR=0.01, FAR=0.001
- ROC-AUC
- EER (Equal Error Rate)

---

## Phase 8 — Liveness / Anti-Spoofing (MODEL 9)

### Architecture

```
Live Photo → Face Crop → Anti-Spoof Model → [LIVE, SPOOF, UNCERTAIN]
```

### Strategy
- Use CelebA-Spoof subset for training (~2 GB, sampled)
- Fine-tune a MobileNetV3-Small or EfficientNet-B0 for binary live/spoof
- Existing stub uses Laplacian variance (sharpness heuristic) — keep as fallback
- For a faster alternative: use MiniFASNet (Silent-Face-Anti-Spoofing, pretrained)

### Config: `ml/config/liveness.yaml`

```yaml
model: mobilenet_v3_small
pretrained: imagenet
num_classes: 2
image_size: 128
batch_size: 32
epochs: 15
learning_rate: 0.0003
optimizer: AdamW
mixed_precision: true
seed: 42
```

---

## Phase 9 — Document Validation (RULE ENGINE)

### Strategy
- **Primarily rule-based** — no neural network needed
- Already partially implemented in Spring Boot backend

### Validation Rules

| Rule | Logic |
|---|---|
| Expiry Check | `expiry_date > today` |
| DOB Sanity | `DOB < today`, age in [0, 150] |
| MRZ Checksums | All 4 check digits pass (already implemented) |
| Document Number Format | Regex per document type |
| Required Fields | All mandatory fields non-empty |
| Nationality Consistency | MRZ nationality matches issuing country |
| Cross-Zone Match | MRZ fields match VIZ (OCR) fields |
| Blacklist Lookup | Against MOCK data only |

---

## Phase 10 — Risk Engine (RULE-BASED)

### Architecture

```
Signal Weights:
  ocr_failure:          15
  mrz_checksum_fail:    20
  expired_document:     10
  tampering_score:      25  (scaled from model output)
  photo_tampering:      15
  face_mismatch:        20
  liveness_failure:     25
  blacklist_match:      30
  cross_zone_mismatch:  15

risk_score = weighted_sum / max_possible × 100
risk_level = LOW (0-30) | MEDIUM (31-60) | HIGH (61-100)
```

### Output Format

```json
{
  "risk_score": 87,
  "risk_level": "HIGH",
  "reasons": [
    "MRZ checksum failed",
    "Possible text tampering (score: 0.78)",
    "Face mismatch (score: 0.32)"
  ]
}
```

---

## Phase 11 — FastAPI Integration

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/ml/ocr` | OCR + field extraction |
| POST | `/ml/mrz` | MRZ extraction + validation |
| POST | `/ml/tampering` | Tampering detection + heatmap |
| POST | `/ml/face-verification` | Face matching + embedding |
| POST | `/ml/liveness` | Anti-spoofing check |
| POST | `/ml/verify-document` | **Unified pipeline** (all of the above) |

### Unified Response

```json
{
  "document": { "type": "PASSPORT", "confidence": 0.95 },
  "ocr": { "fields": {...}, "confidence": 0.92 },
  "mrz": { "valid": true, "checks": {...} },
  "validation": { "expired": false, "rules_passed": 8, "rules_failed": 0 },
  "tampering": { "score": 0.12, "type": "NONE", "heatmap": "..." },
  "face": { "match_score": 0.88, "status": "MATCH" },
  "liveness": { "score": 0.97, "status": "LIVE" },
  "risk": { "score": 15, "level": "LOW", "reasons": [] }
}
```

---

## Phase 12 — Final Evaluation

### Deliverables

| File | Content |
|---|---|
| `ml/evaluation/ocr_metrics.json` | OCR accuracy per field |
| `ml/evaluation/mrz_metrics.json` | MRZ parse/checksum accuracy |
| `ml/evaluation/tampering_metrics.json` | P/R/F1/AUC/FPR/FNR |
| `ml/evaluation/face_metrics.json` | FAR/FRR/TAR/EER |
| `ml/evaluation/liveness_metrics.json` | Spoof detection rates |
| `ml/evaluation/risk_engine_test_results.json` | End-to-end test cases |
| `ml/evaluation/confusion_matrix.png` | Tampering confusion matrix |
| `ml/evaluation/roc_curve.png` | Tampering ROC curve |
| `ml/evaluation/FINAL_MODEL_REPORT.md` | Complete evaluation report |

### Test Cases

| # | Test Case | Expected |
|---|---|---|
| 1 | Genuine passport | LOW risk |
| 2 | Genuine ID | LOW risk |
| 3 | Genuine DL | LOW risk |
| 4 | Expired document | MEDIUM risk |
| 5 | Invalid MRZ | HIGH risk |
| 6 | Text tampering | HIGH risk |
| 7 | Photo-region tampering | HIGH risk |
| 8 | Stamp anomaly | MEDIUM–HIGH risk |
| 9 | Face match (same person) | MATCH |
| 10 | Face mismatch (different person) | MISMATCH |
| 11 | Liveness failure (printed photo) | SPOOF |
| 12 | Multiple failures | HIGH risk |

---

## Data Leakage Prevention

| Rule | Implementation |
|---|---|
| Split by document identity | Group by document source, NOT random frames |
| No image in both train+test | Dedup by perceptual hash |
| No person in both sets | Split by subject ID where available |
| Video sequences together | All frames from one video in same split |
| Ratios | 70% train / 15% val / 15% test |
| Stratification | Equal class distribution across splits |

---

## Compute Optimization (4 GB VRAM)

| Technique | Application |
|---|---|
| Mixed Precision (AMP) | All training runs |
| Gradient Accumulation | Effective batch size 32–64 |
| Image Size 224×224 | Standard for classification |
| Lazy Data Loading | PyTorch DataLoader with workers |
| Model Freezing | Freeze backbone initially, then unfreeze |
| Gradient Checkpointing | If VRAM is tight |
| Pin Memory | Faster CPU→GPU transfer |

---

## Model Export Plan

| Model | Primary Format | Secondary |
|---|---|---|
| Tampering (EfficientNet-B0) | `.pt` | `.onnx` |
| Stamp (ResNet18) | `.pt` | `.onnx` |
| Liveness (MobileNetV3) | `.pt` | `.onnx` |
| OCR (PaddleOCR) | Pretrained (paddle format) | — |
| Face (InsightFace) | Pretrained (ONNX) | — |

---

## Next Immediate Action

> [!IMPORTANT]
> **READY TO PROCEED.** Both SYSTEM_REPORT.md and TRAINING_PLAN.md are complete.
> 
> **Next step:** Phase 0 — Install PyTorch CUDA build, verify GPU access, then begin Phase 1 dataset acquisition.
