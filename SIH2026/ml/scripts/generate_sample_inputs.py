"""Generate Sample Input Files for SIH26188 AI-Based Document & Identity Screening.
Creates sample input images in the `sample_inputs/` directory for manual testing, model inspection, or web portal upload.
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from ml.scripts.dataset_generator import (
    generate_synthetic_passport_data,
    render_document_image,
    apply_tampering,
    create_synthetic_portrait
)

def main():
    output_dir = ROOT_DIR / "sample_inputs"
    output_dir.mkdir(exist_ok=True)

    print("===============================================================")
    print("  SIH26188 AI Model Test Sample Input Generator")
    print("===============================================================")

    # 1. Genuine Valid Passport
    doc1 = generate_synthetic_passport_data(101)
    doc1["documentNumber"] = "Z9876543"
    doc1["surname"] = "SHARMA"
    doc1["givenName"] = "AARAV"
    img1 = render_document_image(doc1, seed=101)
    path1 = output_dir / "01_genuine_passport.png"
    img1.save(path1)
    print(f"[SUCCESS] Generated Genuine Passport Sample: {path1}")

    # 2. Forged ELA Passport (Photo Replacement)
    doc2 = generate_synthetic_passport_data(202)
    doc2["documentNumber"] = "P1234567"
    doc2["surname"] = "FICTITIOUS"
    doc2["givenName"] = "JOHN"
    img2_gen = render_document_image(doc2, seed=202)
    img2_tamp, _ = apply_tampering(img2_gen, doc2, "PHOTO_REPLACEMENT", seed=202)
    path2 = output_dir / "02_forged_ela_passport.png"
    img2_tamp.save(path2)
    print(f"[TAMPERED] Generated Forged ELA Passport Sample: {path2}")

    # 3. Text Manipulation Tampered Passport
    doc3 = generate_synthetic_passport_data(303)
    img3_gen = render_document_image(doc3, seed=303)
    img3_tamp, _ = apply_tampering(img3_gen, doc3, "TEXT_MANIPULATION", seed=303)
    path3 = output_dir / "03_text_tampered_passport.png"
    img3_tamp.save(path3)
    print(f"[TAMPERED] Generated Text Tampered Passport Sample: {path3}")

    # 4. Watchlist Hit Passport
    doc4 = generate_synthetic_passport_data(404)
    doc4["documentNumber"] = "X9988776"
    doc4["surname"] = "SUSPECT"
    doc4["givenName"] = "ANON"
    img4 = render_document_image(doc4, seed=404)
    path4 = output_dir / "04_watchlist_hit_passport.png"
    img4.save(path4)
    print(f"[WATCHLIST] Generated Watchlist Hit Passport Sample: {path4}")

    # 5. Matching Live Subject Portrait
    portrait_match = create_synthetic_portrait(size=(160, 200), seed=101)
    path5 = output_dir / "05_live_subject_photo.png"
    portrait_match.save(path5)
    print(f"[PORTRAIT] Generated Matching Live Subject Photo: {path5}")

    # 6. Impostor Live Subject Portrait
    portrait_impostor = create_synthetic_portrait(size=(160, 200), seed=888)
    path6 = output_dir / "06_impostor_live_photo.png"
    portrait_impostor.save(path6)
    print(f"[PORTRAIT] Generated Impostor Live Subject Photo: {path6}")

    print("\n---------------------------------------------------------------")
    print(f"All sample input files generated in: {output_dir}")
    print("You can upload these files in the Web Station UI (http://localhost:5173/verify)")
    print("---------------------------------------------------------------")

if __name__ == "__main__":
    main()
