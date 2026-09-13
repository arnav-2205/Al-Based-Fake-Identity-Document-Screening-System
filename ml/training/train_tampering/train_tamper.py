"""EfficientNet-B0 Tampering Detection Training and Evaluation Pipeline.
Trains a transfer-learning convolutional neural network to discriminate
between genuine and digitally manipulated identity documents.

Supports the SIH26188_tampering_starter_dataset layout:
  {split}/genuine/*.jpg       -> label 0
  {split}/tampered_text/*.jpg -> label 1
  {split}/tampered_photo/*.jpg-> label 1
  {split}/tampered_stamp/*.jpg-> label 1
"""
import os
import sys
import yaml
import json
import time
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "tampering.yaml"

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

torch.manual_seed(config["seed"])
np.random.seed(config["seed"])

# ---------------------------------------------------------------------------
# Dataset — reads the 4-class folder structure, maps to binary labels
# ---------------------------------------------------------------------------
CLASS_MAP = {
    "genuine": 0,
    "tampered_text": 1,
    "tampered_photo": 1,
    "tampered_stamp": 1,
}

# For 4-class metrics we also track the original class name
CLASS_NAMES_4 = ["genuine", "tampered_text", "tampered_photo", "tampered_stamp"]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class DocumentTamperDataset(Dataset):
    """Loads images from the 4-subfolder layout and maps to binary labels.
    Also stores the original 4-class label index for per-class analysis.
    """

    def __init__(self, data_dir: Path, transform=None):
        self.samples = []  # (path, binary_label, class4_idx)
        self.transform = transform

        for class_name in CLASS_NAMES_4:
            class_dir = data_dir / class_name
            if not class_dir.exists():
                continue
            binary_label = CLASS_MAP[class_name]
            class4_idx = CLASS_NAMES_4.index(class_name)
            for p in sorted(class_dir.iterdir()):
                if p.suffix.lower() in IMAGE_EXTS:
                    self.samples.append((str(p), binary_label, class4_idx))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label, class4 = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label, class4


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------
def get_transforms(img_size: int):
    train_tf = transforms.Compose([
        transforms.Resize((img_size + 16, img_size + 16)),
        transforms.RandomCrop((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.3),
        transforms.RandomRotation(degrees=5),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.02),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.15, scale=(0.02, 0.15)),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_tf, eval_tf


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
def build_model(num_classes: int = 2) -> nn.Module:
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3, inplace=True),
        nn.Linear(in_features, num_classes),
    )
    return model


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------
def train_tampering():
    print("=" * 72)
    print("  EfficientNet-B0 Tampering Detection — Full Training Pipeline")
    print("=" * 72)

    # ---- Resolve dataset path ----
    # Prefer the user-uploaded starter dataset if it exists
    starter_root = BASE_DIR.parent / "SIH26188_tampering_starter_dataset"
    legacy_root = BASE_DIR / "datasets" / "tampering"

    if starter_root.exists():
        data_root = starter_root
        print(f"Using starter dataset: {data_root}")
    elif legacy_root.exists():
        data_root = legacy_root
        print(f"Using legacy dataset: {data_root}")
    else:
        print(f"ERROR: No dataset found. Checked:\n  {starter_root}\n  {legacy_root}")
        sys.exit(1)

    img_size = config["image_size"]
    train_tf, eval_tf = get_transforms(img_size)

    train_ds = DocumentTamperDataset(data_root / "train", transform=train_tf)
    val_ds = DocumentTamperDataset(data_root / "val", transform=eval_tf)
    test_ds = DocumentTamperDataset(data_root / "test", transform=eval_tf)

    print(f"\nDataset split counts:")
    print(f"  Train : {len(train_ds)}")
    print(f"  Val   : {len(val_ds)}")
    print(f"  Test  : {len(test_ds)}")

    if len(train_ds) == 0:
        print("ERROR: Training set is empty! Check dataset folder structure.")
        sys.exit(1)

    # Print per-class distribution
    for split_name, ds in [("Train", train_ds), ("Val", val_ds), ("Test", test_ds)]:
        counts = {}
        for _, _, c4 in ds.samples:
            name = CLASS_NAMES_4[c4]
            counts[name] = counts.get(name, 0) + 1
        print(f"  {split_name} breakdown: {counts}")

    train_loader = DataLoader(
        train_ds, batch_size=config["batch_size"], shuffle=True, num_workers=0, pin_memory=True
    )
    val_loader = DataLoader(
        val_ds, batch_size=config["batch_size"], shuffle=False, num_workers=0, pin_memory=True
    )
    test_loader = DataLoader(
        test_ds, batch_size=config["batch_size"], shuffle=False, num_workers=0, pin_memory=True
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nTraining on device: {device}")

    model = build_model(config["num_classes"]).to(device)
    
    # Weighted loss to handle class imbalance (3:1 tampered-to-genuine ratio)
    genuine_count = sum(1 for _, lbl, _ in train_ds.samples if lbl == 0)
    tampered_count = sum(1 for _, lbl, _ in train_ds.samples if lbl == 1)
    weight_genuine = tampered_count / max(genuine_count, 1)
    weight_tampered = genuine_count / max(tampered_count, 1)
    class_weights = torch.tensor([weight_genuine, weight_tampered], dtype=torch.float32).to(device)
    # Normalize so weights sum to 2
    class_weights = class_weights / class_weights.sum() * 2.0
    print(f"Class weights: genuine={class_weights[0]:.4f}, tampered={class_weights[1]:.4f}")
    
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"]
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config["epochs"])

    ckpt_dir = BASE_DIR / config["checkpoint_dir"]
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    best_val_f1 = 0.0
    best_epoch = 0
    patience_counter = 0
    patience = config.get("early_stopping_patience", 5)
    history = []

    start_time = time.time()

    for epoch in range(1, config["epochs"] + 1):
        # ---- Training phase ----
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for imgs, labels, _ in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(labels)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == labels).sum().item()
            total += len(labels)

        scheduler.step()
        train_loss = total_loss / len(train_ds)
        train_acc = correct / total

        # ---- Validation phase ----
        model.eval()
        val_preds, val_targets, val_probs = [], [], []
        with torch.no_grad():
            for imgs, labels, _ in val_loader:
                imgs = imgs.to(device)
                logits = model(imgs)
                probs = torch.softmax(logits, dim=1)[:, 1]
                preds = torch.argmax(logits, dim=1)

                val_probs.extend(probs.cpu().numpy().tolist())
                val_preds.extend(preds.cpu().numpy().tolist())
                val_targets.extend(labels.numpy().tolist())

        val_acc = accuracy_score(val_targets, val_preds)
        val_prec = precision_score(val_targets, val_preds, zero_division=0)
        val_rec = recall_score(val_targets, val_preds, zero_division=0)
        val_f1 = f1_score(val_targets, val_preds, zero_division=0)
        val_auc = roc_auc_score(val_targets, val_probs) if len(set(val_targets)) > 1 else 1.0

        lr_now = optimizer.param_groups[0]["lr"]
        print(
            f"Epoch [{epoch:02d}/{config['epochs']:02d}] "
            f"Loss: {train_loss:.4f}  TrainAcc: {train_acc:.4f}  |  "
            f"ValAcc: {val_acc:.4f}  ValF1: {val_f1:.4f}  ValAUC: {val_auc:.4f}  "
            f"LR: {lr_now:.6f}"
        )

        history.append({
            "epoch": epoch,
            "trainLoss": round(train_loss, 4),
            "trainAcc": round(train_acc, 4),
            "valAcc": round(val_acc, 4),
            "valPrecision": round(val_prec, 4),
            "valRecall": round(val_rec, 4),
            "valF1": round(val_f1, 4),
            "valAuc": round(val_auc, 4),
            "lr": round(lr_now, 8),
        })

        if val_f1 >= best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            patience_counter = 0
            torch.save(model.state_dict(), ckpt_dir / "best_model.pt")
            print(f"  -> New best model saved (F1={val_f1:.4f})")
        else:
            patience_counter += 1

        torch.save(model.state_dict(), ckpt_dir / "last_model.pt")

        if patience_counter >= patience:
            print(f"\nEarly stopping triggered at epoch {epoch} (no improvement for {patience} epochs).")
            break

    elapsed = time.time() - start_time
    print(f"\nTraining completed in {elapsed:.1f}s. Best Epoch: {best_epoch} (Val F1: {best_val_f1:.4f})")

    # ======================================================================
    # Final Test Set Evaluation
    # ======================================================================
    print("\n" + "=" * 72)
    print("  Evaluating Best Model on Held-out Test Set")
    print("=" * 72)

    model.load_state_dict(torch.load(ckpt_dir / "best_model.pt", weights_only=True))
    model.eval()

    test_preds, test_targets, test_probs = [], [], []
    test_class4_labels = []
    with torch.no_grad():
        for imgs, labels, class4 in test_loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1)[:, 1]
            preds = torch.argmax(logits, dim=1)

            test_probs.extend(probs.cpu().numpy().tolist())
            test_preds.extend(preds.cpu().numpy().tolist())
            test_targets.extend(labels.numpy().tolist())
            test_class4_labels.extend(class4.numpy().tolist())

    test_acc = accuracy_score(test_targets, test_preds)
    test_prec = precision_score(test_targets, test_preds, zero_division=0)
    test_rec = recall_score(test_targets, test_preds, zero_division=0)
    test_f1 = f1_score(test_targets, test_preds, zero_division=0)
    test_auc = roc_auc_score(test_targets, test_probs)

    cm = confusion_matrix(test_targets, test_preds)
    tn, fp, fn, tp = cm.ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    # Per-class (4-class) accuracy breakdown
    per_class_results = {}
    for cls_idx, cls_name in enumerate(CLASS_NAMES_4):
        mask = [i for i, c in enumerate(test_class4_labels) if c == cls_idx]
        if not mask:
            continue
        cls_preds = [test_preds[i] for i in mask]
        cls_targets = [test_targets[i] for i in mask]
        cls_acc = accuracy_score(cls_targets, cls_preds)
        per_class_results[cls_name] = {
            "count": len(mask),
            "accuracy": round(float(cls_acc), 4),
            "correctlyClassified": sum(1 for p, t in zip(cls_preds, cls_targets) if p == t),
        }

    eval_metrics = {
        "model": "EfficientNet-B0 Tamper Detector",
        "dataset": "SIH26188_tampering_starter_dataset",
        "testSamples": len(test_ds),
        "trainSamples": len(train_ds),
        "valSamples": len(val_ds),
        "bestEpoch": best_epoch,
        "totalEpochsTrained": len(history),
        "trainingTimeSeconds": round(elapsed, 1),
        "accuracy": round(float(test_acc), 4),
        "precision": round(float(test_prec), 4),
        "recall": round(float(test_rec), 4),
        "f1Score": round(float(test_f1), 4),
        "rocAuc": round(float(test_auc), 4),
        "falsePositiveRate": round(float(fpr), 4),
        "falseNegativeRate": round(float(fnr), 4),
        "confusionMatrix": {
            "trueNegative": int(tn),
            "falsePositive": int(fp),
            "falseNegative": int(fn),
            "truePositive": int(tp),
        },
        "perClassResults": per_class_results,
        "trainingHistory": history,
    }

    eval_dir = BASE_DIR / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    with open(eval_dir / "tampering_metrics.json", "w") as f:
        json.dump(eval_metrics, f, indent=2)

    # ---- Confusion Matrix Plot ----
    plt.figure(figsize=(7, 5.5))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=["Genuine", "Tampered"],
        yticklabels=["Genuine", "Tampered"],
    )
    plt.title("Tampering Detection — Confusion Matrix (Test Set)")
    plt.ylabel("Ground Truth")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(eval_dir / "tampering_confusion_matrix.png", dpi=150)
    plt.close()

    # ---- Training Curves Plot ----
    epochs_list = [h["epoch"] for h in history]
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.plot(epochs_list, [h["trainLoss"] for h in history], "b-o", markersize=4, label="Train Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.plot(epochs_list, [h["valAcc"] for h in history], "g-o", markersize=4, label="Val Acc")
    plt.plot(epochs_list, [h["valF1"] for h in history], "r-s", markersize=4, label="Val F1")
    plt.plot(epochs_list, [h["valAuc"] for h in history], "m-^", markersize=4, label="Val AUC")
    plt.xlabel("Epoch")
    plt.ylabel("Score")
    plt.title("Validation Metrics")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ylim(0.0, 1.05)
    
    plt.tight_layout()
    plt.savefig(eval_dir / "tampering_training_curves.png", dpi=150)
    plt.close()

    print(f"\n{'-' * 60}")
    print(f"  Test Accuracy  : {test_acc * 100:.2f}%")
    print(f"  Precision      : {test_prec * 100:.2f}%")
    print(f"  Recall         : {test_rec * 100:.2f}%")
    print(f"  F1 Score       : {test_f1 * 100:.2f}%")
    print(f"  ROC AUC        : {test_auc * 100:.2f}%")
    print(f"  FPR            : {fpr * 100:.2f}%")
    print(f"  FNR            : {fnr * 100:.2f}%")
    print(f"{'-' * 60}")
    print(f"\nPer-class breakdown:")
    for cls_name, info in per_class_results.items():
        print(f"  {cls_name:20s}: {info['correctlyClassified']}/{info['count']} correct ({info['accuracy']*100:.1f}%)")
    print(f"\nMetrics  -> {eval_dir / 'tampering_metrics.json'}")
    print(f"Confusion-> {eval_dir / 'tampering_confusion_matrix.png'}")
    print(f"Curves   -> {eval_dir / 'tampering_training_curves.png'}")
    print(f"Best ckpt-> {ckpt_dir / 'best_model.pt'}")


if __name__ == "__main__":
    train_tampering()
