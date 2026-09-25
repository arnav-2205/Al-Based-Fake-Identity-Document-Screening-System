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
    build_passport_data,
    render_document_image,
    apply_tampering,
    create_synthetic_portrait
)


def _save_with_mrz_exif(img, path, mrz_str):
    exif = img.getexif()
    exif[0x9286] = f"<MRZ>{mrz_str}</MRZ>"
    # Also save with standard PNG or JPEG
    img.save(path, exif=exif)


def main():
    output_dir = ROOT_DIR / "sample_inputs"
    output_dir.mkdir(exist_ok=True)

    print("===============================================================")
    print("  SIH26188 AI Model Test Sample Input Generator")
    print("===============================================================")

    # 1. Genuine Valid Passport (Aarav Sharma)
    doc1 = build_passport_data(
        surname="SHARMA",
        given_name="AARAV",
        document_number="Z9876543",
        date_of_birth="1985-04-12",
        gender="M",
        expiry_date="2032-05-18",
        nationality="IND",
        place_of_issue="NEW DELHI",
        idx=101
    )
    img1 = render_document_image(doc1, seed=101)
    path1 = output_dir / "01_genuine_passport.png"
    _save_with_mrz_exif(img1, path1, doc1["mrz"])
    print(f"[SUCCESS] Generated Genuine Passport Sample: {path1}")

    # 2. Forged ELA Passport (Photo Replacement - John Fictitious)
    doc2 = build_passport_data(
        surname="FICTITIOUS",
        given_name="JOHN",
        document_number="P1234567",
        date_of_birth="1985-04-12",
        gender="M",
        expiry_date="2032-05-18",
        nationality="IND",
        place_of_issue="MUMBAI",
        idx=202
    )
    img2_gen = render_document_image(doc2, seed=202)
    img2_tamp, _ = apply_tampering(img2_gen, doc2, "PHOTO_REPLACEMENT", seed=202)
    path2 = output_dir / "02_forged_ela_passport.png"
    _save_with_mrz_exif(img2_tamp, path2, doc2["mrz"])
    print(f"[TAMPERED] Generated Forged ELA Passport Sample: {path2}")

    # 3. Text Manipulation Tampered Passport (Aarav Sharma with VIZ Expiry Altered to 2039-12-31)
    doc3 = build_passport_data(
        surname="SHARMA",
        given_name="AARAV",
        document_number="Z9876543",
        date_of_birth="1985-04-12",
        gender="M",
        expiry_date="2032-05-18",
        nationality="IND",
        place_of_issue="NEW DELHI",
        idx=303
    )
    img3_gen = render_document_image(doc3, seed=303)
    img3_tamp, _ = apply_tampering(img3_gen, doc3, "TEXT_MANIPULATION", seed=303)
    path3 = output_dir / "03_text_tampered_passport.png"
    _save_with_mrz_exif(img3_tamp, path3, doc3["mrz"])
    print(f"[TAMPERED] Generated Text Tampered Passport Sample: {path3}")

    # 4. Watchlist Hit Passport (Anon Suspect matching seeded DB entry X9988776)
    doc4 = build_passport_data(
        surname="SUSPECT",
        given_name="ANON",
        document_number="X9988776",
        date_of_birth="1990-11-02",
        gender="M",
        expiry_date="2030-08-15",
        nationality="IND",
        place_of_issue="KOLKATA",
        idx=404
    )
    img4 = render_document_image(doc4, seed=404)
    path4 = output_dir / "04_watchlist_hit_passport.png"
    _save_with_mrz_exif(img4, path4, doc4["mrz"])
    print(f"[WATCHLIST] Generated Watchlist Hit Passport Sample: {path4}")

    # 5. Matching Live Subject Portrait (Matching Aarav Sharma - seed 101)
    portrait_match = create_synthetic_portrait(size=(160, 200), seed=101)
    path5 = output_dir / "05_live_subject_photo.png"
    portrait_match.save(path5)
    print(f"[PORTRAIT] Generated Matching Live Subject Photo: {path5}")

    # 6. Impostor Live Subject Portrait (Different face - seed 888)
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

