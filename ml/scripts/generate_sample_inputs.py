"""Generate Sample Input Files for SIH26188 AI-Based Document & Identity Screening.
Creates sample input images in the `sample_inputs/` directory for manual testing, model inspection, or web portal upload.
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw
from ml.scripts.dataset_generator import (
    build_passport_data,
    render_document_image,
    apply_tampering,
    create_synthetic_portrait,
    _get_font,
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

    # 7. Genuine Republic of India Entry Visa
    visa_img = Image.new("RGB", (800, 520), color=(240, 253, 244))
    visa_draw = ImageDraw.Draw(visa_img)
    visa_font_hdr = _get_font(18)
    visa_font_lbl = _get_font(12)
    visa_font_val = _get_font(15)
    visa_font_mrz = _get_font(20, mono=True)
    visa_draw.rectangle([15, 15, 785, 505], outline=(16, 185, 129), width=2)
    visa_draw.text((40, 30), "REPUBLIC OF INDIA - ENTRY VISA", fill=(15, 23, 42), font=visa_font_hdr)
    visa_draw.text((40, 60), "VISA NO: V9842105  •  TYPE: TOURIST / MULTIPLE ENTRY", fill=(4, 120, 87), font=visa_font_lbl)
    
    # Portrait on Visa
    visa_portrait = create_synthetic_portrait(size=(150, 190), seed=505)
    visa_img.paste(visa_portrait, (40, 95))
    visa_draw.rectangle([40, 95, 190, 285], outline=(100, 116, 139), width=1)
    
    visa_draw.text((220, 100), "SURNAME / GIVEN NAME:", fill=(100, 116, 139), font=visa_font_lbl)
    visa_draw.text((220, 120), "WATSON EMILY", fill=(15, 23, 42), font=visa_font_val)
    visa_draw.text((220, 160), "PASSPORT NO / NATIONALITY:", fill=(100, 116, 139), font=visa_font_lbl)
    visa_draw.text((220, 180), "Z7654321 / GBR", fill=(15, 23, 42), font=visa_font_val)
    visa_draw.text((220, 220), "DURATION OF STAY:", fill=(100, 116, 139), font=visa_font_lbl)
    visa_draw.text((220, 240), "90 DAYS (MULTIPLE)", fill=(4, 120, 87), font=visa_font_val)
    
    visa_draw.text((500, 100), "VALID FROM / VALID UNTIL:", fill=(100, 116, 139), font=visa_font_lbl)
    visa_draw.text((500, 120), "01 JAN 2026 / 31 DEC 2028", fill=(15, 23, 42), font=visa_font_val)
    visa_draw.text((500, 160), "PLACE OF ISSUE:", fill=(100, 116, 139), font=visa_font_lbl)
    visa_draw.text((500, 180), "LONDON (HCI)", fill=(15, 23, 42), font=visa_font_val)
    
    visa_mrz_l1 = "V<INDWATSON<<EMILY<<<<<<<<<<<<<<<<<<<<<<<<<<"
    visa_mrz_l2 = "V9842105<4GBR8806152F2812318<<<<<<<<<<<<<<<02"
    visa_draw.rectangle([20, 410, 780, 495], fill=(10, 25, 47))
    visa_draw.text((35, 422), visa_mrz_l1, fill=(110, 231, 183), font=visa_font_mrz)
    visa_draw.text((35, 455), visa_mrz_l2, fill=(110, 231, 183), font=visa_font_mrz)
    path7 = output_dir / "07_genuine_entry_visa.png"
    _save_with_mrz_exif(visa_img, path7, f"{visa_mrz_l1}\n{visa_mrz_l2}")
    print(f"[VISA] Generated Genuine Entry Visa Sample: {path7}")

    # 8. Genuine Driving Licence (DL-0420110023456)
    dl_img = Image.new("RGB", (800, 520), color=(241, 245, 249))
    dl_draw = ImageDraw.Draw(dl_img)
    dl_font_hdr = _get_font(18)
    dl_font_lbl = _get_font(12)
    dl_font_val = _get_font(15)
    dl_draw.rectangle([15, 15, 785, 505], outline=(59, 130, 246), width=2)
    dl_draw.text((40, 30), "UNION OF INDIA - DRIVING LICENCE", fill=(15, 23, 42), font=dl_font_hdr)
    dl_draw.text((40, 60), "TRANSPORT DEPARTMENT, DELHI  •  LICENCE NO: DL-0420110023456", fill=(29, 78, 216), font=dl_font_lbl)
    
    # Portrait on DL
    dl_portrait = create_synthetic_portrait(size=(150, 190), seed=606)
    dl_img.paste(dl_portrait, (40, 95))
    dl_draw.rectangle([40, 95, 190, 285], outline=(100, 116, 139), width=1)
    
    dl_draw.text((220, 100), "NAME OF HOLDER:", fill=(100, 116, 139), font=dl_font_lbl)
    dl_draw.text((220, 120), "VIKRAM SINGH", fill=(15, 23, 42), font=dl_font_val)
    dl_draw.text((220, 160), "DATE OF BIRTH / BLOOD GROUP:", fill=(100, 116, 139), font=dl_font_lbl)
    dl_draw.text((220, 180), "15-08-1988  •  B+ POSITIVE", fill=(15, 23, 42), font=dl_font_val)
    dl_draw.text((220, 220), "CLASS OF VEHICLES (COV):", fill=(100, 116, 139), font=dl_font_lbl)
    dl_draw.text((220, 240), "LMV, MCWG", fill=(29, 78, 216), font=dl_font_val)
    
    dl_draw.text((500, 100), "ISSUE DATE / VALID TILL:", fill=(100, 116, 139), font=dl_font_lbl)
    dl_draw.text((500, 120), "10-04-2015 / 14-08-2038", fill=(15, 23, 42), font=dl_font_val)
    dl_draw.text((500, 160), "ISSUING AUTHORITY:", fill=(100, 116, 139), font=dl_font_lbl)
    dl_draw.text((500, 180), "RTO RAJPUR ROAD (DL-04)", fill=(15, 23, 42), font=dl_font_val)
    
    dl_draw.rectangle([20, 410, 780, 495], fill=(30, 41, 59))
    dl_draw.text((35, 430), "OPTICAL DRIVING LICENCE SECURITY STRIP & DIGITAL SARATHI CHIP VERIFIED", fill=(147, 197, 253), font=_get_font(14, mono=True))
    dl_draw.text((35, 460), "ISSUED UNDER MOTOR VEHICLES ACT 1988  •  GOVERNMENT OF NCT OF DELHI", fill=(203, 213, 225), font=_get_font(12, mono=True))
    
    path8 = output_dir / "08_genuine_driving_licence.png"
    dl_img.save(path8)
    print(f"[DL] Generated Genuine Driving Licence Sample: {path8}")

    print("\n---------------------------------------------------------------")
    print(f"All sample input files generated in: {output_dir}")
    print("You can upload these files in the Web Station UI (http://localhost:5173/verify)")
    print("---------------------------------------------------------------")


if __name__ == "__main__":
    main()

