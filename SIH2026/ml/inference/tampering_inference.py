"""Comprehensive Multi-Signal Document Tampering & Forgery Inference Engine.
Combines:
  1. Deep CNN Tamper Classifier (SIDTD EfficientNet-B3, pre-trained on MIDV2020)
  2. Error Level Analysis (ELA) with Heatmap Generation
  3. ROI-level Photo / Text / Stamp Region Analysis
  4. Digital Forensics & EXIF Metadata Inspection
"""
import io
import base64
import cv2
import torch
import numpy as np
from PIL import Image, ImageChops, ExifTags
from torchvision import transforms
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from ml.inference.copy_move import detect_copy_move, detect_font_inconsistency

BASE_DIR = Path(__file__).resolve().parent.parent
CKPT_PATH = BASE_DIR / "checkpoints" / "tampering" / "best_model.pt"
SIDTD_CKPT_PATH = BASE_DIR / "checkpoints" / "tampering" / "sidtd_efficientnet_b3.pth"

_EDITOR_SIGNATURES = (
    "photoshop", "gimp", "lightroom", "affinity", "paint.net",
    "pixlr", "snapseed", "canva", "picsart", "adobe", "exiftool"
)

class TamperingInferenceEngine:
    def __init__(self, checkpoint_path: Path = CKPT_PATH, decision_threshold: float = 0.35):
        self.decision_threshold = decision_threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # SIDTD EfficientNet-B3 uses 300x300 input
        self.transform = transforms.Compose([
            transforms.Resize((300, 300)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        # Build SIDTD EfficientNet-B3 architecture (2-class: real/fake)
        from efficientnet_pytorch import EfficientNet
        self.model = EfficientNet.from_name("efficientnet-b3", num_classes=2)
        
        # Try loading fine-tuned weights first, fall back to SIDTD pretrained
        self.model_loaded = False
        for ckpt in [checkpoint_path, SIDTD_CKPT_PATH]:
            if ckpt.exists():
                try:
                    state = torch.load(ckpt, map_location=self.device, weights_only=False)
                    self.model.load_state_dict(state)
                    self.model_loaded = True
                    print(f"[TamperingEngine] Loaded weights from {ckpt.name}")
                    break
                except Exception as e:
                    print(f"[TamperingEngine] Could not load {ckpt.name}: {e}")
        
        if not self.model_loaded:
            print("[TamperingEngine] WARNING: No trained weights found, using random init!")
            
        self.model.eval().to(self.device)

    def compute_ela(self, image: Image.Image, quality: int = 90) -> Tuple[float, str, Dict[str, float]]:
        """Computes JPEG compression error level analysis and heatmap."""
        rgb_img = image.convert("RGB")
        buf = io.BytesIO()
        rgb_img.save(buf, "JPEG", quality=quality)
        buf.seek(0)
        recompressed = Image.open(buf).convert("RGB")
        
        diff = ImageChops.difference(rgb_img, recompressed)
        arr = np.asarray(diff).astype(np.float32)
        mag = arr.mean(axis=2)
        max_mag = float(mag.max()) or 1.0
        norm = mag / max_mag
        
        hot_fraction = float((norm > 0.35).mean())
        spread = float(norm.std())
        ela_score = float(np.clip(0.6 * hot_fraction * 6.0 + 0.4 * spread * 3.0, 0.0, 1.0))
        
        # Amplified heatmap PNG
        heat = np.clip(norm * 255.0 * 3.0, 0, 255).astype(np.uint8)
        heat_img = Image.fromarray(heat).convert("L")
        out_buf = io.BytesIO()
        heat_img.save(out_buf, "PNG")
        heatmap_b64 = base64.b64encode(out_buf.getvalue()).decode("ascii")
        
        return ela_score, heatmap_b64, {"hotFraction": round(hot_fraction, 4), "spread": round(spread, 4)}

    def inspect_exif(self, image: Image.Image) -> Dict[str, Any]:
        """Audits image EXIF tags for graphic design tool signatures."""
        res = {"hasExif": False, "software": None, "editorDetected": False, "notes": []}
        try:
            exif = image.getexif()
            if not exif:
                res["notes"].append("No EXIF metadata embedded")
                return res
            res["hasExif"] = True
            tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
            software = str(tags.get("Software", "") or "")
            res["software"] = software or None
            if any(h in software.lower() for h in _EDITOR_SIGNATURES):
                res["editorDetected"] = True
                res["notes"].append(f"Image editor trace detected: {software}")
        except Exception as e:
            res["notes"].append(f"EXIF read error: {e}")
        return res

    def compute_region_scores(self, image: Image.Image) -> Dict[str, float]:
        """Calculates localized tampering likelihood for photo, text, and stamp ROIs."""
        rgb_img = image.convert("RGB")
        w, h = rgb_img.size
        
        buf = io.BytesIO()
        rgb_img.save(buf, "JPEG", quality=90)
        buf.seek(0)
        recompressed = Image.open(buf).convert("RGB")
        arr = np.asarray(ImageChops.difference(rgb_img, recompressed)).astype(np.float32).mean(axis=2)
        norm = arr / (float(arr.max()) or 1.0)
        
        def sub_score(x0, y0, x1, y1):
            sub = norm[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
            return float(np.clip((sub > 0.35).mean() * 5.0, 0.0, 1.0)) if sub.size > 0 else 0.0
            
        return {
            "photoTampering": round(sub_score(0.0, 0.1, 0.3, 0.6), 4),
            "textTampering": round(sub_score(0.3, 0.1, 1.0, 0.7), 4),
            "stampTampering": round(sub_score(0.6, 0.35, 1.0, 0.75), 4)
        }

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        """Performs full multi-modal tampering evaluation."""
        notes = []
        
        # 1. CNN Model Inference
        img_t = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(img_t)
            probs = torch.softmax(logits, dim=1)
            cnn_tamper_score = float(probs[0, 1].cpu().item())
            
        # 2. ELA & Heatmap
        ela_score, heatmap_b64, ela_stats = self.compute_ela(image)
        notes.append(f"ELA Response: HotFraction={ela_stats['hotFraction']}, Spread={ela_stats['spread']}")
        
        # 3. EXIF Check
        exif = self.inspect_exif(image)
        notes.extend(exif.get("notes", []))
        exif_penalty = 0.25 if exif.get("editorDetected") else 0.0
        
        # 4. Region Scores
        regions = self.compute_region_scores(image)

        # 5. Copy-move (cloned region) + font/glyph consistency — catch
        # clean digit/text swaps that leave no compression artifact for
        # ELA to find.
        bgr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        copy_move_score, copy_move_stats = detect_copy_move(bgr, min_cluster=15)
        font_score, font_stats = detect_font_inconsistency(bgr)
        if copy_move_score > 0:
            notes.append(
                f"Copy-move: {copy_move_stats['matchedClusters']} keypoints share shift "
                f"{copy_move_stats.get('dominantShift')}"
            )
        if font_score > 0:
            notes.append(
                f"Font inconsistency: {font_stats['heightOutlierFraction']*100:.1f}% of glyphs "
                f"deviate from median height {font_stats.get('medianGlyphHeight')}px"
            )

        # Composite Multi-Signal Tampering Score
        # Combines weighted multi-signal sum with peak forensic alarm
        max_forensic_alarm = max(cnn_tamper_score, ela_score, copy_move_score, font_score)
        weighted_sum = (
            0.55 * cnn_tamper_score
            + 0.20 * ela_score
            + exif_penalty
            + 0.08 * max(regions.values())
            + 0.08 * copy_move_score
            + 0.09 * font_score
        )
        composite_score = float(np.clip(
            0.60 * weighted_sum + 0.40 * max_forensic_alarm,
            0.0, 1.0
        ))

        is_tampered = composite_score >= self.decision_threshold

        # Text region tampering score
        text_tampering = round(min(1.0, (
            regions["textTampering"]
            + 0.5 * font_score
            + (0.35 * copy_move_score if copy_move_score >= 0.4 else 0.0)
            + (0.40 * (cnn_tamper_score - 0.3) if cnn_tamper_score >= 0.35 else 0.0)
        )), 4)

        # Infer predominant tampering type
        if is_tampered:
            if copy_move_score >= 0.4:
                tamper_type = "COPY_MOVE_FORGERY"
            elif font_score >= 0.4:
                tamper_type = "FONT_INCONSISTENCY"
            elif cnn_tamper_score >= 0.4:
                tamper_type = "TEXT_TAMPERING" if text_tampering > regions["photoTampering"] else "PHOTO_TAMPERING"
            else:
                reg_max = max(regions, key=regions.get)
                if regions[reg_max] > 0.3:
                    tamper_type = reg_max.replace("Tampering", "").upper()
                else:
                    tamper_type = "DIGITAL_COMPRESSION_ANOMALY"
        else:
            tamper_type = "NONE"

        return {
            "tamperingScore": round(composite_score, 4),
            "cnnScore": round(cnn_tamper_score, 4),
            "elaScore": round(ela_score, 4),
            "copyMoveScore": round(copy_move_score, 4),
            "fontInconsistencyScore": round(font_score, 4),
            "isTampered": is_tampered,
            "tamperType": tamper_type,
            "photoTampering": round(min(1.0, regions["photoTampering"] + exif_penalty), 4),
            "textTampering": text_tampering,
            "stampTampering": round(regions["stampTampering"], 4),
            "elaHeatmapBase64": heatmap_b64,
            "exif": exif,
            "threshold": self.decision_threshold,
            "notes": notes,
            "copyMove": copy_move_stats,
            "fontConsistency": font_stats,
        }
