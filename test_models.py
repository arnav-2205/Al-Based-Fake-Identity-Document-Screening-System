"""Quick Test Runner for SIH26188 AI Document & Identity Screening Pipeline.
Runs defensive AI models on sample input files and prints complete diagnostic results.
"""
import os
import sys
from pathlib import Path
from PIL import Image

# Ensure project root is in import path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from ml.inference.document_pipeline import UnifiedDocumentVerificationPipeline

def run_test():
    print("===============================================================")
    print("   SIH26188 AI Screening Pipeline Test Runner")
    print("===============================================================")

    pipeline = UnifiedDocumentVerificationPipeline()

    sample_dir = ROOT_DIR / "sample_inputs"
    if not sample_dir.exists():
        print("Sample inputs directory missing. Run: python ml/scripts/generate_sample_inputs.py")
        return

    test_cases = [
        ("01_genuine_passport.png", "05_live_subject_photo.png", "Genuine Passport + Matching Face"),
        ("02_forged_ela_passport.png", "05_live_subject_photo.png", "Forged ELA Passport (Photo Replacement)"),
        ("03_text_tampered_passport.png", "05_live_subject_photo.png", "Text Tampered Passport"),
        ("04_watchlist_hit_passport.png", "06_impostor_live_photo.png", "Watchlist Hit + Impostor Face"),
    ]

    for doc_file, face_file, desc in test_cases:
        doc_path = sample_dir / doc_file
        face_path = sample_dir / face_file

        if not doc_path.exists() or not face_path.exists():
            continue

        print(f"\n---------------------------------------------------------------")
        print(f"TEST CASE: {desc}")
        print(f"Doc Input:  {doc_path.name}")
        print(f"Face Input: {face_path.name}")
        print(f"---------------------------------------------------------------")

        doc_img = Image.open(doc_path)
        face_img = Image.open(face_path)

        result = pipeline.verify_document(
            document_image=doc_img,
            live_photo=face_img
        )

        risk = result.get("risk", {})
        validation = result.get("validation", {})
        tampering = result.get("tampering", {})
        face = result.get("face", {})

        print(f" [VERDICT]     Final Result:     {validation.get('finalResult', 'N/A')}")
        print(f" [RISK LEVEL]  Level:            {risk.get('riskLevel', 'N/A')} (Score: {risk.get('riskScore', 0)})")
        print(f" [TAMPERING]   Composite Score:  {(tampering.get('compositeTamperingScore', 0.0)*100):.1f}%")
        print(f" [FACE MATCH]  Status:           {face.get('faceMatchStatus', 'N/A')} (Score: {(face.get('faceMatchScore', 0.0)*100):.1f}%)")
        print(f" [REASONS]     Risk Drivers:     {', '.join(risk.get('reasons', ['None']))}")

    print("\n===============================================================")
    print("  Test Pipeline Execution Complete!")
    print("===============================================================")

if __name__ == "__main__":
    run_test()
