"""Dataset Generator and Curator for SIH26188 AI-Based Document Screening System.

Generates high-fidelity synthetic document datasets, tampering pairs,
stamp datasets, MRZ test suites, and face verification pairs strictly adhering
to safety policies (synthetic identities, no real PII, no data leakage).
"""
import os
import json
import random
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pathlib import Path

# Fix random seed for full reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
DATA_DIR = BASE_DIR / "data"

for d in [
    DATASETS_DIR / "documents" / "train",
    DATASETS_DIR / "documents" / "val",
    DATASETS_DIR / "documents" / "test",
    DATASETS_DIR / "tampering" / "train" / "genuine",
    DATASETS_DIR / "tampering" / "train" / "tampered",
    DATASETS_DIR / "tampering" / "val" / "genuine",
    DATASETS_DIR / "tampering" / "val" / "tampered",
    DATASETS_DIR / "tampering" / "test" / "genuine",
    DATASETS_DIR / "tampering" / "test" / "tampered",
    DATASETS_DIR / "stamps" / "train" / "genuine",
    DATASETS_DIR / "stamps" / "train" / "forged",
    DATASETS_DIR / "stamps" / "val" / "genuine",
    DATASETS_DIR / "stamps" / "val" / "forged",
    DATASETS_DIR / "stamps" / "test" / "genuine",
    DATASETS_DIR / "stamps" / "test" / "forged",
    DATASETS_DIR / "faces" / "train" / "live",
    DATASETS_DIR / "faces" / "train" / "spoof",
    DATASETS_DIR / "faces" / "val" / "live",
    DATASETS_DIR / "faces" / "val" / "spoof",
    DATASETS_DIR / "faces" / "test" / "live",
    DATASETS_DIR / "faces" / "test" / "spoof",
    DATASETS_DIR / "mrz",
    DATASETS_DIR / "manifests",
    DATASETS_DIR / "metadata",
]:
    d.mkdir(parents=True, exist_ok=True)

# Synthetic Indian & International Names & Cities for Defensive Document Simulation
SURNAMES = ["SHARMA", "VERMA", "KUMAR", "SINGH", "PATEL", "GUPTA", "REDDY", "RAO", "KHAN", "MEHTA", "DAS", "JOSHI", "NAIR", "CHOUDHURY", "BANERJEE", "DUTTA", "GOWDA", "MENON"]
GIVEN_NAMES = ["AARAV", "VIHAAN", "ADITYA", "ROHAN", "PRIYA", "ANANYA", "POOJA", "NEHA", "RAHUL", "SANJAY", "AMIT", "SNEHA", "DEEPAK", "KAVITA", "SUNIL", "RITU"]
NATIONALITIES = ["IND", "USA", "GBR", "CAN", "AUS", "DEU", "FRA", "SGP", "JPN"]
CITIES = ["NEW DELHI", "MUMBAI", "BENGALURU", "HYDERABAD", "CHENNAI", "KOLKATA", "AHMEDABAD", "PUNE", "JAIPUR", "LUCKNOW"]

def compute_mrz_check_digit(data: str) -> int:
    weights = (7, 3, 1)
    total = 0
    for i, c in enumerate(data):
        if c == '<':
            val = 0
        elif c.isdigit():
            val = int(c)
        elif 'A' <= c <= 'Z':
            val = ord(c) - ord('A') + 10
        else:
            val = 0
        total += val * weights[i % 3]
    return total % 10

def generate_synthetic_passport_data(idx: int):
    surname = SURNAMES[idx % len(SURNAMES)]
    given_name = GIVEN_NAMES[(idx * 3) % len(GIVEN_NAMES)]
    nationality = "IND" if (idx % 3 != 0) else NATIONALITIES[idx % len(NATIONALITIES)]
    
    # Format: 1 Letter + 7 Digits (Indian passport format) -> padded to 9 chars for ICAO TD3
    raw_num = f"{chr(65 + (idx % 26))}{1000000 + (idx * 37) % 8999999}"
    doc_num = raw_num
    doc_num_mrz = doc_num.ljust(9, '<')[:9]
    doc_num_chk = compute_mrz_check_digit(doc_num_mrz)
    
    # DOB: YYMMDD
    yy = 70 + (idx * 2) % 30
    mm = 1 + (idx * 3) % 12
    dd = 1 + (idx * 7) % 28
    dob_mrz = f"{yy:02d}{mm:02d}{dd:02d}"
    dob_chk = compute_mrz_check_digit(dob_mrz)
    dob_iso = f"19{yy:02d}-{mm:02d}-{dd:02d}"
    
    gender = "M" if (idx % 2 == 0) else "F"
    
    # Expiry: YYMMDD (Future valid dates 2028-2037)
    exp_yy = 28 + (idx * 2) % 10
    exp_mm = 1 + (idx * 5) % 12
    exp_dd = 1 + (idx * 11) % 28
    exp_mrz = f"{exp_yy:02d}{exp_mm:02d}{exp_dd:02d}"
    exp_chk = compute_mrz_check_digit(exp_mrz)
    exp_iso = f"20{exp_yy:02d}-{exp_mm:02d}-{exp_dd:02d}"
    
    # Optional field: exact 14 chars
    raw_opt = f"Z{100000 + (idx * 19) % 899999}"
    opt_field = raw_opt.ljust(14, '<')[:14]
    opt_chk = compute_mrz_check_digit(opt_field)
    
    # TD3 MRZ Lines (44 characters each)
    line1 = f"P<{nationality}{surname}<<{given_name}".ljust(44, '<')[:44]
    comp_data = f"{doc_num_mrz}{doc_num_chk}{dob_mrz}{dob_chk}{exp_mrz}{exp_chk}{opt_field}{opt_chk}"
    final_chk = compute_mrz_check_digit(comp_data)
    line2 = f"{doc_num_mrz}{doc_num_chk}{nationality}{dob_mrz}{dob_chk}{gender}{exp_mrz}{exp_chk}{opt_field}{opt_chk}{final_chk}".ljust(44, '<')[:44]
    
    return {
        "id": f"DOC_{idx:05d}",
        "type": "PASSPORT",
        "surname": surname,
        "givenName": given_name,
        "fullName": f"{given_name} {surname}",
        "nationality": nationality,
        "documentNumber": doc_num,
        "dateOfBirth": dob_iso,
        "gender": gender,
        "expiryDate": exp_iso,
        "placeOfIssue": CITIES[idx % len(CITIES)],
        "mrz": f"{line1}\n{line2}",
        "mrzValid": True,
    }

def create_synthetic_portrait(size=(160, 200), seed=42):
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", size, color=(220 + rng.integers(0, 30), 225 + rng.integers(0, 25), 235 + rng.integers(0, 20)))
    draw = ImageDraw.Draw(img)
    
    # Head & Shoulders silhouette / portrait structure
    skin_tones = [(240, 200, 160), (220, 175, 140), (195, 145, 110), (160, 115, 85)]
    skin = skin_tones[seed % len(skin_tones)]
    
    # Shoulders / Clothes
    shirt_colors = [(40, 70, 120), (30, 30, 40), (180, 50, 50), (45, 120, 75), (90, 60, 120)]
    shirt = shirt_colors[seed % len(shirt_colors)]
    draw.ellipse([-20, size[1]-70, size[0]+20, size[1]+90], fill=shirt)
    
    # Neck
    draw.rectangle([size[0]//2 - 18, size[1]//2 + 10, size[0]//2 + 18, size[1]//2 + 50], fill=skin)
    
    # Face Oval
    face_w, face_h = 75, 95
    cx, cy = size[0]//2, size[1]//2 - 10
    draw.ellipse([cx - face_w//2, cy - face_h//2, cx + face_w//2, cy + face_h//2], fill=skin)
    
    # Hair
    hair_colors = [(30, 25, 20), (50, 35, 25), (15, 15, 15)]
    hair = hair_colors[seed % len(hair_colors)]
    draw.ellipse([cx - face_w//2 - 4, cy - face_h//2 - 10, cx + face_w//2 + 4, cy - 10], fill=hair)
    
    # Eyes & Eyebrows
    draw.rectangle([cx - 20, cy - 10, cx - 8, cy - 6], fill=(40, 30, 20))
    draw.rectangle([cx + 8, cy - 10, cx + 20, cy - 6], fill=(40, 30, 20))
    draw.line([cx - 22, cy - 16, cx - 6, cy - 16], fill=hair, width=2)
    draw.line([cx + 6, cy - 16, cx + 22, cy - 16], fill=hair, width=2)
    
    # Nose & Mouth
    draw.line([cx, cy - 4, cx - 2, cy + 12], fill=(skin[0]-35, skin[1]-35, skin[2]-35), width=2)
    draw.line([cx - 2, cy + 12, cx + 3, cy + 12], fill=(skin[0]-35, skin[1]-35, skin[2]-35), width=2)
    draw.line([cx - 12, cy + 24, cx + 12, cy + 24], fill=(160, 70, 70), width=2)
    
    return img

def create_synthetic_stamp(size=(120, 120), seed=42, forged=False):
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    color = (180, 20, 30, 200) if not forged else (150, 30, 30, 140)
    
    # Outer ring
    draw.ellipse([5, 5, size[0]-5, size[1]-5], outline=color, width=3)
    draw.ellipse([12, 12, size[0]-12, size[1]-12], outline=color, width=1)
    
    # Center text / Star / Date
    draw.text((size[0]//2 - 35, size[1]//2 - 15), "IMMIGRATION", fill=color)
    draw.text((size[0]//2 - 25, size[1]//2), "VERIFIED", fill=color)
    draw.text((size[0]//2 - 28, size[1]//2 + 14), f"2026-08-{10 + (seed % 18):02d}", fill=color)
    
    if forged:
        # Artifacts: blur, broken boundary, smear, double imprint
        img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
        overlay = Image.new("RGBA", size, (255, 255, 255, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.ellipse([8, 8, size[0]-8, size[1]-8], outline=(170, 40, 40, 90), width=2)
        img = Image.alpha_composite(img, overlay)
    
    return img.rotate(seed % 30 - 15, resample=Image.BICUBIC, expand=False)

def render_document_image(doc_data: dict, seed: int) -> Image.Image:
    width, height = 800, 520
    # Background security pattern
    bg = Image.new("RGB", (width, height), color=(248, 246, 240))
    draw = ImageDraw.Draw(bg)
    
    # Guilloche / fine security line simulation
    for y in range(0, height, 8):
        draw.line([(0, y), (width, y)], fill=(238, 235, 225), width=1)
    for x in range(0, width, 16):
        draw.line([(x, 0), (x, height)], fill=(242, 238, 230), width=1)
        
    # Header Band
    draw.rectangle([0, 0, width, 60], fill=(24, 48, 89))
    draw.text((30, 18), "GOVERNMENT OF INDIA / PASSPORT", fill=(255, 255, 255))
    draw.text((width - 160, 18), "REPUBLIC OF INDIA", fill=(210, 225, 245))
    
    # Portrait
    portrait = create_synthetic_portrait(size=(140, 180), seed=seed)
    bg.paste(portrait, (40, 85))
    draw.rectangle([38, 83, 182, 267], outline=(150, 160, 175), width=2)
    
    # Visual Inspection Zone (VIZ) Text
    fields = [
        ("Type / Type", doc_data["type"]),
        ("Country Code / Pays", doc_data["nationality"]),
        ("Passport No. / No du passeport", doc_data["documentNumber"]),
        ("Surname / Nom", doc_data["surname"]),
        ("Given Name(s) / Prenoms", doc_data["givenName"]),
        ("Nationality / Nationalite", doc_data["nationality"]),
        ("Date of Birth / Date de naissance", doc_data["dateOfBirth"]),
        ("Sex / Sexe", doc_data["gender"]),
        ("Place of Issue / Lieu de delivrance", doc_data["placeOfIssue"]),
        ("Date of Expiry / Date d'expiration", doc_data["expiryDate"]),
    ]
    
    start_x, start_y = 220, 85
    for i, (label, val) in enumerate(fields):
        col = i // 5
        row = i % 5
        x = start_x + (col * 280)
        y = start_y + (row * 36)
        draw.text((x, y), label.upper(), fill=(110, 120, 135))
        draw.text((x, y + 14), str(val), fill=(10, 15, 25))
        
    # Stamp
    stamp = create_synthetic_stamp(size=(110, 110), seed=seed, forged=False)
    bg.paste(stamp, (width - 170, 220), stamp)
    
    # MRZ Zone (Bottom Band)
    draw.rectangle([0, height - 120, width, height], fill=(255, 255, 255))
    draw.line([(0, height - 120), (width, height - 120)], fill=(180, 190, 200), width=1)
    
    mrz_lines = doc_data["mrz"].split("\n")
    draw.text((35, height - 100), mrz_lines[0], fill=(20, 20, 20))
    draw.text((35, height - 60), mrz_lines[1], fill=(20, 20, 20))
    
    return bg

def apply_tampering(img: Image.Image, doc_data: dict, tamper_type: str, seed: int) -> tuple[Image.Image, dict]:
    tampered = img.copy()
    details = {"type": tamper_type, "modifiedFields": [], "bbox": []}
    draw = ImageDraw.Draw(tampered)
    
    if tamper_type == "PHOTO_REPLACEMENT":
        # Splicing in a completely different face portrait with compression & edge mismatch
        diff_portrait = create_synthetic_portrait(size=(140, 180), seed=seed + 999)
        # Apply slight blur and tone shift to simulate spliced photo
        enhancer = ImageEnhance.Color(diff_portrait)
        diff_portrait = enhancer.enhance(1.4)
        tampered.paste(diff_portrait, (40, 85))
        # Add subtle seam line
        draw.rectangle([39, 84, 181, 266], outline=(100, 100, 100), width=1)
        details["modifiedFields"].append("portrait")
        details["bbox"].append([40, 85, 180, 265])
        
    elif tamper_type == "TEXT_MANIPULATION":
        # Alter expiry date or document number in VIZ without changing MRZ (Cross-zone mismatch)
        new_exp = "2039-12-31"
        # White out previous text region and write altered text
        draw.rectangle([500, 228, 700, 258], fill=(248, 246, 240))
        draw.text((500, 242), new_exp, fill=(5, 5, 5))
        details["modifiedFields"].append("expiryDate")
        details["bbox"].append([500, 228, 700, 258])
        
    elif tamper_type == "STAMP_FORGERY":
        # Overwrite with forged/smudged stamp
        forged_stamp = create_synthetic_stamp(size=(110, 110), seed=seed, forged=True)
        tampered.paste(forged_stamp, (img.width - 170, 220), forged_stamp)
        details["modifiedFields"].append("stamp")
        details["bbox"].append([img.width - 170, 220, img.width - 60, 330])
        
    elif tamper_type == "MRZ_CHECKSUM_TAMPER":
        # Tamper a character in the MRZ line
        mrz_lines = doc_data["mrz"].split("\n")
        l2 = list(mrz_lines[1])
        l2[2] = '8' if l2[2] != '8' else '9' # Tamper passport number character
        tampered_mrz_l2 = "".join(l2)
        draw.rectangle([0, img.height - 75, img.width, img.height], fill=(255, 255, 255))
        draw.text((35, img.height - 60), tampered_mrz_l2, fill=(20, 20, 20))
        details["modifiedFields"].append("mrz")
        details["bbox"].append([35, img.height - 75, img.width - 35, img.height - 30])
        
    return tampered, details

def generate_all_datasets(total_samples=1000):
    print(f"Generating {total_samples} defensive ML dataset samples...")
    manifest = []
    
    # 70% Train, 15% Val, 15% Test
    train_n = int(total_samples * 0.70)
    val_n = int(total_samples * 0.15)
    test_n = total_samples - train_n - val_n
    
    tamper_types = ["PHOTO_REPLACEMENT", "TEXT_MANIPULATION", "STAMP_FORGERY", "MRZ_CHECKSUM_TAMPER"]
    
    for i in range(total_samples):
        if i < train_n:
            split = "train"
        elif i < train_n + val_n:
            split = "val"
        else:
            split = "test"
            
        doc_data = generate_synthetic_passport_data(i)
        genuine_img = render_document_image(doc_data, seed=i)
        
        # Save Genuine document
        gen_filename = f"{doc_data['id']}_genuine.png"
        gen_path = DATASETS_DIR / "tampering" / split / "genuine" / gen_filename
        genuine_img.save(gen_path)
        
        manifest.append({
            "id": doc_data["id"],
            "split": split,
            "filename": str(gen_path.relative_to(DATASETS_DIR)),
            "label": "GENUINE",
            "isTampered": False,
            "tamperType": "NONE",
            "metadata": doc_data,
        })
        
        # Generate paired Tampered version
        tamper_type = tamper_types[i % len(tamper_types)]
        tampered_img, tamper_details = apply_tampering(genuine_img, doc_data, tamper_type, seed=i)
        
        tamp_filename = f"{doc_data['id']}_tampered_{tamper_type.lower()}.png"
        tamp_path = DATASETS_DIR / "tampering" / split / "tampered" / tamp_filename
        tampered_img.save(tamp_path)
        
        manifest.append({
            "id": f"{doc_data['id']}_TAMP",
            "split": split,
            "filename": str(tamp_path.relative_to(DATASETS_DIR)),
            "label": "TAMPERED",
            "isTampered": True,
            "tamperType": tamper_type,
            "tamperDetails": tamper_details,
            "metadata": doc_data,
        })
        
        # Generate stamp samples
        stamp_gen = create_synthetic_stamp(seed=i, forged=False).convert("RGB")
        stamp_gen_path = DATASETS_DIR / "stamps" / split / "genuine" / f"stamp_{i:04d}_gen.png"
        stamp_gen.save(stamp_gen_path)
        
        stamp_forg = create_synthetic_stamp(seed=i, forged=True).convert("RGB")
        stamp_forg_path = DATASETS_DIR / "stamps" / split / "forged" / f"stamp_{i:04d}_forg.png"
        stamp_forg.save(stamp_forg_path)
        
        # Generate face live / spoof pairs
        face_live = create_synthetic_portrait(size=(160, 200), seed=i)
        face_live_path = DATASETS_DIR / "faces" / split / "live" / f"face_{i:04d}_live.png"
        face_live.save(face_live_path)
        
        # Spoof: screen glare / low quality / printed artifact
        face_spoof = face_live.copy()
        if i % 2 == 0:
            face_spoof = face_spoof.filter(ImageFilter.GaussianBlur(radius=2.5))
        else:
            enhancer = ImageEnhance.Contrast(face_spoof)
            face_spoof = enhancer.enhance(1.9)
        face_spoof_path = DATASETS_DIR / "faces" / split / "spoof" / f"face_{i:04d}_spoof.png"
        face_spoof.save(face_spoof_path)
        
    # Write global manifest
    manifest_path = DATASETS_DIR / "manifests" / "dataset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Generated {len(manifest)} manifest records.")
    print(f"Datasets successfully populated at: {DATASETS_DIR}")

if __name__ == "__main__":
    generate_all_datasets(total_samples=400)
