import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import cv2
import numpy as np
from app.services.text_manipulation import analyze_text_manipulation, localize_field_boxes
from app.services.ocr_engine import extract as ocr_extract

def test_clean_document_text_manipulation():
    # Load clean synthetic passport fixture
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_inputs", "07_clean_synthetic_passport.png")
    assert os.path.exists(fixture_path), f"Fixture not found: {fixture_path}"

    with open(fixture_path, "rb") as f:
        img_bytes = f.read()

    ocr_res = ocr_extract(img_bytes)
    img = cv2.imread(fixture_path)

    res = analyze_text_manipulation(img, ocr_result=ocr_res)
    print("Clean Document Forensic Result:", res)
    assert res["status"] in ["NOT_DETECTED", "CLEAR"], f"Expected clean document text manipulation to be NOT_DETECTED, got {res['status']}"
    assert len(res["suspiciousFields"]) == 0, f"Expected 0 suspicious fields, got {res['suspiciousFields']}"
    print("Test A Passed: Clean document text manipulation state =", res["status"])

def test_altered_text_manipulation():
    # Load clean synthetic passport and artificially overlay digital patch text on passport number zone
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_inputs", "07_clean_synthetic_passport.png")
    with open(fixture_path, "rb") as f:
        img_bytes = f.read()

    ocr_res = ocr_extract(img_bytes)
    img = cv2.imread(fixture_path)
    h, w = img.shape[:2]

    # Get actual localized ROI for passport number
    boxes = ocr_res.get("ocrBoxes") or ocr_res.get("visualZone", {}).get("ocrBoxes") or []
    rois = localize_field_boxes(w, h, ocr_res.get("fields", {}), boxes)

    pn_roi = rois.get("passportNumber") or rois.get("documentNumber") or (int(w * 0.55), int(h * 0.12), int(w * 0.90), int(h * 0.28))
    rx0, ry0, rx1, ry1 = pn_roi

    altered_img = img.copy()
    # Artificial white patch with high contrast noise and sharp boundary line
    altered_img[ry0:ry1, rx0:rx1] = 255
    cv2.putText(altered_img, "X99999999", (rx0 + 5, ry0 + int((ry1-ry0)*0.7)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.rectangle(altered_img, (rx0, ry0), (rx1, ry1), (0, 0, 255), 3)

    print("Extracted ROIs:", rois)
    print("Passport ROI:", pn_roi)
    res = analyze_text_manipulation(altered_img, ocr_result=ocr_res)
    print("Forensic Result:", res)
    assert res["status"] == "SUSPICIOUS", f"Expected altered text document to be SUSPICIOUS, got {res['status']}"
    assert len(res["reasons"]) > 0, "Expected forensic reasons for text manipulation"
    print("Test B Passed: Artificially altered text region detected as SUSPICIOUS:", res["suspiciousFields"], res["reasons"])

def test_ocr_low_quality_text_manipulation():
    # Low-contrast image with noisy OCR output
    noisy_img = np.ones((400, 600, 3), dtype=np.uint8) * 180
    cv2.putText(noisy_img, "LOW QUALITY SCANNED TEXT", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 80, 80), 1)

    ocr_stub = {
        "fields": {"name": "LOW QUALITY SCANNED TEXT"},
        "visualZone": {"ocrBoxes": [{"text": "LOW QUALITY", "xmin": 50, "ymin": 130, "xmax": 300, "ymax": 170}]},
        "fieldConfidences": {"name": 0.35}
    }

    res = analyze_text_manipulation(noisy_img, ocr_result=ocr_stub)

    assert res["status"] in ["NOT_DETECTED", "INCONCLUSIVE"], f"Expected low quality OCR image to be NOT_DETECTED/INCONCLUSIVE, got {res['status']}"
    assert res["status"] != "SUSPICIOUS", "Low OCR quality must NOT automatically be flagged as text manipulation"
    print("Test C Passed: Low quality OCR image handled gracefully without false positive:", res["status"])

def test_no_text_document_text_manipulation():
    # Plain blank image
    blank_img = np.zeros((400, 600, 3), dtype=np.uint8)

    res = analyze_text_manipulation(blank_img)

    assert res["status"] in ["NOT_DETECTED", "INCONCLUSIVE"], f"Expected no text document to be NOT_DETECTED or INCONCLUSIVE, got {res['status']}"
    print("Test D Passed: No text document handled gracefully:", res["status"])

if __name__ == "__main__":
    test_clean_document_text_manipulation()
    test_altered_text_manipulation()
    test_ocr_low_quality_text_manipulation()
    test_no_text_document_text_manipulation()
    print("ALL P1.2 TEXT MANIPULATION UNIT TESTS PASSED SUCCESSFULLY!")
