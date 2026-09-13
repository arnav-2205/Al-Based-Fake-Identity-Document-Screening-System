"""ResNet18 Immigration Stamp Verification Training and Evaluation Pipeline.
Classifies document stamps as Genuine or Forged/Manipulated.
"""
import yaml
import json
import time
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
from pathlib import Path
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "stamp.yaml"

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

torch.manual_seed(config["seed"])

class StampDataset(Dataset):
    def __init__(self, data_dir: Path, transform=None):
        self.samples = []
        self.transform = transform
        
        gen_dir = data_dir / "genuine"
        forg_dir = data_dir / "forged"
        
        if gen_dir.exists():
            for p in gen_dir.glob("*.png"):
                self.samples.append((str(p), 0))
        if forg_dir.exists():
            for p in forg_dir.glob("*.png"):
                self.samples.append((str(p), 1))
                
    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

def train_stamp():
    print("=== Phase 6: Training ResNet18 Stamp Verification Model ===")
    data_root = BASE_DIR / "datasets" / "stamps"
    img_size = config["image_size"]
    
    tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    train_ds = StampDataset(data_root / "train", transform=tf)
    val_ds = StampDataset(data_root / "val", transform=tf)
    test_ds = StampDataset(data_root / "test", transform=tf)
    
    train_loader = DataLoader(train_ds, batch_size=config["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=config["batch_size"], shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=config["batch_size"], shuffle=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, config["num_classes"])
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"])
    
    ckpt_dir = BASE_DIR / config["checkpoint_dir"]
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    
    best_f1 = 0.0
    for epoch in range(1, config["epochs"] + 1):
        model.train()
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            
        model.eval()
        val_preds, val_targets = [], []
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs = imgs.to(device)
                preds = torch.argmax(model(imgs), dim=1)
                val_preds.extend(preds.cpu().numpy().tolist())
                val_targets.extend(labels.numpy().tolist())
                
        f1 = f1_score(val_targets, val_preds, zero_division=0)
        if f1 >= best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), ckpt_dir / "best_model.pt")
            
    # Evaluate on Test set
    model.load_state_dict(torch.load(ckpt_dir / "best_model.pt", weights_only=True))
    model.eval()
    test_preds, test_targets, test_probs = [], [], []
    with torch.no_grad():
        for imgs, labels in test_loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1)[:, 1]
            preds = torch.argmax(logits, dim=1)
            test_probs.extend(probs.cpu().numpy().tolist())
            test_preds.extend(preds.cpu().numpy().tolist())
            test_targets.extend(labels.numpy().tolist())
            
    acc = accuracy_score(test_targets, test_preds)
    f1 = f1_score(test_targets, test_preds, zero_division=0)
    prec = precision_score(test_targets, test_preds, zero_division=0)
    rec = recall_score(test_targets, test_preds, zero_division=0)
    auc = roc_auc_score(test_targets, test_probs)
    
    metrics = {
        "model": "ResNet18 Stamp Authenticator",
        "testSamples": len(test_ds),
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1Score": round(float(f1), 4),
        "rocAuc": round(float(auc), 4),
    }
    
    with open(BASE_DIR / "evaluation" / "stamp_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Stamp Model Test Accuracy: {acc*100:.2f}% | F1 Score: {f1*100:.2f}%")

if __name__ == "__main__":
    train_stamp()
