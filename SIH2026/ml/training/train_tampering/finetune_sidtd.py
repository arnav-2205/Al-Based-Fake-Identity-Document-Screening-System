"""Fine-tune SIDTD EfficientNet-B3 on the local SIH26188 starter dataset.

The SIDTD pretrained weights come from the CVC research group's balanced
templates partition (genuine vs forged identity documents from MIDV2020).
We fine-tune on our local 4-class dataset (genuine / tampered_text /
tampered_photo / tampered_stamp → binary) to adapt to our domain.
"""
import os
import sys
import time
import json
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix,
)

BASE_DIR = Path(r"c:\Users\swami\Desktop\SIH26188\ml")
SIDTD_CKPT = BASE_DIR / "checkpoints" / "tampering" / "sidtd_efficientnet_b3.pth"
OUTPUT_CKPT = BASE_DIR / "checkpoints" / "tampering" / "best_model.pt"
LAST_CKPT = BASE_DIR / "checkpoints" / "tampering" / "last_model.pt"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
CLASS_MAP = {"genuine": 0, "tampered_text": 1, "tampered_photo": 1, "tampered_stamp": 1}
CLASS_NAMES_4 = ["genuine", "tampered_text", "tampered_photo", "tampered_stamp"]

# SIDTD used 300×300 for EfficientNet-B3
IMG_SIZE = 300
BATCH_SIZE = 16
EPOCHS = 15
LR = 1e-4
PATIENCE = 5
SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)


class DocumentTamperDataset(Dataset):
    def __init__(self, data_dir: Path, transform=None):
        self.samples = []
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


def get_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE + 20, IMG_SIZE + 20)),
        transforms.RandomCrop((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(p=0.3),
        transforms.RandomRotation(degrees=5),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.02),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_tf, eval_tf


def build_sidtd_model():
    """Build EfficientNet-B3 with SIDTD pretrained weights."""
    from efficientnet_pytorch import EfficientNet

    model = EfficientNet.from_name("efficientnet-b3", num_classes=2)
    if SIDTD_CKPT.exists():
        state = torch.load(SIDTD_CKPT, map_location="cpu", weights_only=False)
        model.load_state_dict(state)
        print(f"[OK] Loaded SIDTD pretrained weights from {SIDTD_CKPT}")
    else:
        print(f"[WARN] SIDTD checkpoint not found at {SIDTD_CKPT}, using random init")
    return model


def finetune():
    print("=" * 72)
    print("  Fine-tuning SIDTD EfficientNet-B3 on SIH26188 Starter Dataset")
    print("=" * 72)

    # Find dataset
    project_root = Path(r"c:\Users\swami\Desktop\SIH26188")
    data_root = project_root / "datasets" / "tampering"
    if not data_root.exists():
        print(f"ERROR: No dataset found at {data_root}")
        sys.exit(1)
    print(f"Dataset: {data_root}")

    train_tf, eval_tf = get_transforms()
    train_ds = DocumentTamperDataset(data_root / "train", transform=train_tf)
    val_ds = DocumentTamperDataset(data_root / "val", transform=eval_tf)
    test_ds = DocumentTamperDataset(data_root / "test", transform=eval_tf)

    print(f"\n  Train: {len(train_ds)}  Val: {len(val_ds)}  Test: {len(test_ds)}")

    if len(train_ds) == 0:
        print("ERROR: Training set empty!")
        sys.exit(1)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    model = build_sidtd_model().to(device)

    # Freeze backbone initially, only train classifier
    for param in model.parameters():
        param.requires_grad = False
    for param in model._fc.parameters():
        param.requires_grad = True

    # Weighted loss
    genuine_count = sum(1 for _, lbl, _ in train_ds.samples if lbl == 0)
    tampered_count = sum(1 for _, lbl, _ in train_ds.samples if lbl == 1)
    w0 = tampered_count / max(genuine_count, 1)
    w1 = genuine_count / max(tampered_count, 1)
    weights = torch.tensor([w0, w1], dtype=torch.float32).to(device)
    weights = weights / weights.sum() * 2.0
    print(f"  Class weights: genuine={weights[0]:.4f}, tampered={weights[1]:.4f}")

    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=LR * 5, weight_decay=1e-4)

    # Phase 1: Train classifier only for 3 epochs
    print("\n--- Phase 1: Classifier-only training (3 epochs) ---")
    for epoch in range(1, 4):
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for imgs, labels, _ in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(labels)
            correct += (torch.argmax(logits, dim=1) == labels).sum().item()
            total += len(labels)
        print(f"  Epoch {epoch}: Loss={total_loss/len(train_ds):.4f} Acc={correct/total:.4f}")

    # Phase 2: Unfreeze all, fine-tune end-to-end
    print("\n--- Phase 2: Full fine-tuning ---")
    for param in model.parameters():
        param.requires_grad = True
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_f1 = 0.0
    best_epoch = 0
    patience_counter = 0
    history = []
    start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for imgs, labels, _ in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(labels)
            correct += (torch.argmax(logits, dim=1) == labels).sum().item()
            total += len(labels)
        scheduler.step()
        train_loss = total_loss / len(train_ds)
        train_acc = correct / total

        # Validation
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
        val_f1 = f1_score(val_targets, val_preds, zero_division=0)
        val_auc = roc_auc_score(val_targets, val_probs) if len(set(val_targets)) > 1 else 1.0

        lr_now = optimizer.param_groups[0]["lr"]
        print(
            f"  Epoch [{epoch:02d}/{EPOCHS:02d}] "
            f"Loss={train_loss:.4f} TrainAcc={train_acc:.4f} | "
            f"ValAcc={val_acc:.4f} ValF1={val_f1:.4f} ValAUC={val_auc:.4f} LR={lr_now:.6f}"
        )

        history.append({
            "epoch": epoch, "trainLoss": round(train_loss, 4),
            "trainAcc": round(train_acc, 4), "valAcc": round(val_acc, 4),
            "valF1": round(val_f1, 4), "valAuc": round(val_auc, 4),
        })

        if val_f1 >= best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            patience_counter = 0
            torch.save(model.state_dict(), OUTPUT_CKPT)
            print(f"    >> Best model saved (F1={val_f1:.4f})")
        else:
            patience_counter += 1

        torch.save(model.state_dict(), LAST_CKPT)

        if patience_counter >= PATIENCE:
            print(f"\n  Early stopping at epoch {epoch}")
            break

    elapsed = time.time() - start_time
    print(f"\n  Training completed in {elapsed:.1f}s. Best Epoch: {best_epoch} (F1={best_val_f1:.4f})")

    # Test evaluation
    print("\n" + "=" * 72)
    print("  Final Test Set Evaluation (SIDTD-finetuned)")
    print("=" * 72)

    model.load_state_dict(torch.load(OUTPUT_CKPT, weights_only=False, map_location=device))
    model.eval()

    test_preds, test_targets, test_probs, test_class4 = [], [], [], []
    with torch.no_grad():
        for imgs, labels, c4 in test_loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1)[:, 1]
            preds = torch.argmax(logits, dim=1)
            test_probs.extend(probs.cpu().numpy().tolist())
            test_preds.extend(preds.cpu().numpy().tolist())
            test_targets.extend(labels.numpy().tolist())
            test_class4.extend(c4.numpy().tolist())

    test_acc = accuracy_score(test_targets, test_preds)
    test_prec = precision_score(test_targets, test_preds, zero_division=0)
    test_rec = recall_score(test_targets, test_preds, zero_division=0)
    test_f1 = f1_score(test_targets, test_preds, zero_division=0)
    test_auc = roc_auc_score(test_targets, test_probs)
    cm = confusion_matrix(test_targets, test_preds)
    tn, fp, fn, tp = cm.ravel()

    per_class = {}
    for ci, cn in enumerate(CLASS_NAMES_4):
        mask = [i for i, c in enumerate(test_class4) if c == ci]
        if mask:
            cls_acc = accuracy_score([test_targets[i] for i in mask], [test_preds[i] for i in mask])
            per_class[cn] = {"count": len(mask), "accuracy": round(cls_acc, 4)}

    eval_metrics = {
        "model": "SIDTD EfficientNet-B3 (fine-tuned)",
        "dataset": "SIH26188_tampering_starter_dataset",
        "sidtd_pretrained": True,
        "testSamples": len(test_ds),
        "bestEpoch": best_epoch,
        "accuracy": round(float(test_acc), 4),
        "precision": round(float(test_prec), 4),
        "recall": round(float(test_rec), 4),
        "f1Score": round(float(test_f1), 4),
        "rocAuc": round(float(test_auc), 4),
        "confusionMatrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "perClassResults": per_class,
        "trainingHistory": history,
    }

    eval_dir = BASE_DIR / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(eval_dir / "sidtd_finetune_metrics.json", "w") as f:
        json.dump(eval_metrics, f, indent=2)

    print(f"\n  Accuracy  : {test_acc * 100:.2f}%")
    print(f"  Precision : {test_prec * 100:.2f}%")
    print(f"  Recall    : {test_rec * 100:.2f}%")
    print(f"  F1 Score  : {test_f1 * 100:.2f}%")
    print(f"  ROC AUC   : {test_auc * 100:.2f}%")
    print(f"\n  Per-class:")
    for cn, info in per_class.items():
        print(f"    {cn:20s}: {info['accuracy']*100:.1f}% ({info['count']} samples)")
    print(f"\n  Metrics -> {eval_dir / 'sidtd_finetune_metrics.json'}")
    print(f"  Best ckpt -> {OUTPUT_CKPT}")


if __name__ == "__main__":
    finetune()
