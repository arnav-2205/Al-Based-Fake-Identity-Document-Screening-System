"""Face Liveness & Anti-Spoofing Inference Engine (MobileNetV3 + Frequency Analysis).
Detects 2D presentation attacks, screen replays, printed masks, and texture degradation.
"""
import io
import torch
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms, models
from pathlib import Path
from typing import Dict, Any, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
CKPT_PATH = BASE_DIR / "checkpoints" / "liveness" / "best_model.pt"

class LivenessInferenceEngine:
    def __init__(self, checkpoint_path: Path = CKPT_PATH, liveness_threshold: float = 0.50):
        self.liveness_threshold = liveness_threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        self.model = models.mobilenet_v3_small(weights=None)
        in_features = self.model.classifier[3].in_features
        self.model.classifier[3] = torch.nn.Linear(in_features, 2)
        
        if checkpoint_path.exists():
            try:
                self.model.load_state_dict(torch.load(checkpoint_path, map_location=self.device, weights_only=True))
                self.model_loaded = True
            except Exception:
                self.model_loaded = False
        else:
            self.model_loaded = False
            
        self.model.eval().to(self.device)

    def analyze_texture_sharpness(self, image: Image.Image) -> float:
        """Measures high-frequency Laplacian variance to catch re-photographed screen blur."""
        gray = np.array(image.convert("L"), dtype=np.float32)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())
        return lap_var

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        """Classifies facial image as LIVE or SPOOF."""
        notes = []
        
        # 1. Frequency / Laplacian variance
        lap_var = self.analyze_texture_sharpness(image)
        notes.append(f"Laplacian Sharpness Variance: {lap_var:.1f}")
        
        # 2. Deep Anti-Spoof CNN
        img_t = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(img_t)
            probs = torch.softmax(logits, dim=1)
            # Class 0 = LIVE, Class 1 = SPOOF
            live_prob = float(probs[0, 0].cpu().item())
            spoof_prob = float(probs[0, 1].cpu().item())
            
        # Combine deep model confidence with sharpness heuristic
        if lap_var < 35.0:
            # Extreme blur or low texture strongly signals a printed replica
            composite_live_score = min(live_prob, 0.35)
            notes.append("Low texture frequency detected (indicative of print/screen replay)")
        else:
            composite_live_score = live_prob
            
        status = "LIVE" if composite_live_score >= self.liveness_threshold else "SPOOF"
        
        return {
            "livenessScore": round(composite_live_score, 4),
            "spoofScore": round(1.0 - composite_live_score, 4),
            "livenessStatus": status,
            "laplacianVariance": round(lap_var, 2),
            "threshold": self.liveness_threshold,
            "notes": notes
        }
