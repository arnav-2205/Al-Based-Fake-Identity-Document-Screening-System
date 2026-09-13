"""Create a starter training dataset from sample_inputs by applying
augmentation to produce enough samples for fine-tuning.
"""
import os
import sys
import random
import shutil
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

random.seed(42)
np.random.seed(42)

BASE_DIR = Path(r"c:\Users\swami\Desktop\SIH26188")
SAMPLE_DIR = BASE_DIR / "sample_inputs"
OUT_DIR = BASE_DIR / "datasets" / "tampering"

# Source images and their labels
SOURCES = {
    "genuine": ["01_genuine_passport.png"],
    "tampered_text": ["03_text_tampered_passport.png"],
    "tampered_photo": ["02_forged_ela_passport.png"],
    "tampered_stamp": ["04_watchlist_hit_passport.png"],
}

# Number of augmented variants per source image
AUG_PER_IMAGE = 30


def augment_image(img: Image.Image, idx: int) -> Image.Image:
    """Apply random augmentations to create variants."""
    w, h = img.size

    # Random crop (90-100% of original)
    crop_scale = random.uniform(0.88, 1.0)
    cw, ch = int(w * crop_scale), int(h * crop_scale)
    x = random.randint(0, w - cw)
    y = random.randint(0, h - ch)
    out = img.crop((x, y, x + cw, y + ch)).resize((w, h), Image.LANCZOS)

    # Random rotation
    if random.random() < 0.4:
        angle = random.uniform(-8, 8)
        out = out.rotate(angle, expand=False, fillcolor=(255, 255, 255))

    # Random brightness / contrast
    if random.random() < 0.5:
        factor = random.uniform(0.8, 1.3)
        out = ImageEnhance.Brightness(out).enhance(factor)
    if random.random() < 0.5:
        factor = random.uniform(0.8, 1.3)
        out = ImageEnhance.Contrast(out).enhance(factor)

    # Random color jitter
    if random.random() < 0.3:
        factor = random.uniform(0.85, 1.15)
        out = ImageEnhance.Color(out).enhance(factor)

    # Random sharpness
    if random.random() < 0.3:
        factor = random.uniform(0.5, 2.0)
        out = ImageEnhance.Sharpness(out).enhance(factor)

    # Random blur
    if random.random() < 0.2:
        out = out.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

    # Random noise (very subtle)
    if random.random() < 0.3:
        arr = np.array(out).astype(np.float32)
        noise = np.random.normal(0, random.uniform(3, 8), arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        out = Image.fromarray(arr)

    # Random horizontal flip
    if random.random() < 0.3:
        out = out.transpose(Image.FLIP_LEFT_RIGHT)

    return out


def create_dataset():
    print("=" * 60)
    print("  Creating Tampering Starter Dataset")
    print("=" * 60)

    # Clean up old dataset
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    split_ratios = {"train": 0.7, "val": 0.15, "test": 0.15}

    for class_name, src_files in SOURCES.items():
        all_images = []

        for src_file in src_files:
            src_path = SAMPLE_DIR / src_file
            if not src_path.exists():
                print(f"  [WARN] Source not found: {src_path}")
                continue

            img = Image.open(src_path).convert("RGB")
            # Add original
            all_images.append(img.copy())
            # Add augmented versions
            for i in range(AUG_PER_IMAGE):
                all_images.append(augment_image(img, i))

        random.shuffle(all_images)
        n = len(all_images)
        train_end = int(n * split_ratios["train"])
        val_end = train_end + int(n * split_ratios["val"])

        splits = {
            "train": all_images[:train_end],
            "val": all_images[train_end:val_end],
            "test": all_images[val_end:],
        }

        for split_name, imgs in splits.items():
            split_dir = OUT_DIR / split_name / class_name
            split_dir.mkdir(parents=True, exist_ok=True)
            for j, im in enumerate(imgs):
                im.save(split_dir / f"{class_name}_{j:04d}.png")

        print(f"  {class_name:20s} -> train={len(splits['train']):3d}  val={len(splits['val']):3d}  test={len(splits['test']):3d}")

    print(f"\n  Dataset created at: {OUT_DIR}")
    print("  Done!")


if __name__ == "__main__":
    create_dataset()
