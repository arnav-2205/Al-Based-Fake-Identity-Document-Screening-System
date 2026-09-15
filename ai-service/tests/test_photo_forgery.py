import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import cv2
import numpy as np
from app.services.photo_forgery import analyze_photo_replacement, detect_photo_region

def test_clean_document_photo_forgery():
    # Load clean synthetic passport fixture
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_inputs", "07_clean_synthetic_passport.png")
    assert os.path.exists(fixture_path), f"Fixture not found: {fixture_path}"

    img = cv2.imread(fixture_path)
    res = analyze_photo_replacement(img)

    assert res["status"] in ["NOT_DETECTED", "CLEAR"], f"Expected clean document to be NOT_DETECTED/CLEAR, got {res['status']}"
    assert res["confidence"] > 0.5
    print("Test A Passed: Clean synthetic document photo forgery state =", res["status"])

def test_altered_photo_region_photo_forgery():
    # Load clean synthetic passport and artificially tamper with photo region
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_inputs", "07_clean_synthetic_passport.png")
    img = cv2.imread(fixture_path)

    # Locate photo region
    bbox, conf, notes = detect_photo_region(img)
    assert bbox is not None, "Failed to locate photo region on clean passport"

    x0, y0, x1, y1 = bbox
    w = x1 - x0
    h = y1 - y0
    altered_img = img.copy()

    # Create sharp artificial splice boundary with high contrast block noise
    noise = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    altered_img[y0:y1, x0:x1] = noise

    # Add severe artificial edge seam line around photo border
    cv2.rectangle(altered_img, (x0, y0), (x1, y1), (0, 0, 255), 4)

    res = analyze_photo_replacement(altered_img, photo_box=bbox)

    assert res["status"] == "SUSPICIOUS", f"Expected altered photo region to be SUSPICIOUS, got {res['status']}"
    assert len(res["reasons"]) > 0, "Expected reasons for suspicious photo forgery"
    print("Test B Passed: Artificially altered photo region detected as SUSPICIOUS:", res)

def test_no_photo_document_photo_forgery():
    # Plain text / blank document with no detectable photo
    blank_img = np.ones((400, 600, 3), dtype=np.uint8) * 240
    cv2.putText(blank_img, "PLAIN TEXT DOCUMENT NO PHOTO", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    res = analyze_photo_replacement(blank_img)

    assert res["status"] in ["INCONCLUSIVE", "NOT_DETECTED"], f"Expected no photo document to be INCONCLUSIVE or NOT_DETECTED, got {res['status']}"
    assert res["status"] != "SUSPICIOUS", "Document with no photo must NOT automatically be flagged as forged"
    print("Test C Passed: No photo document handled gracefully:", res["status"])

if __name__ == "__main__":
    test_clean_document_photo_forgery()
    test_altered_photo_region_photo_forgery()
    test_no_photo_document_photo_forgery()
    print("ALL PHOTO FORGERY UNIT TESTS PASSED SUCCESSFULLY!")
