"""Rule-Based Document Validation & Weighted Risk Scoring Engine for SIH26188.
Synthesizes multi-modal ML signals, deterministic cross-zone validations,
and security audit checks into a unified 0-100 risk score with transparent reasons.
"""
from datetime import datetime, date
from typing import Dict, Any, List, Optional

# Mock watchlist/blacklist for safe security testing (Defensive Mock Only)
MOCK_SECURITY_BLACKLIST = {
    "Z9999999", "A1234567", "X9876543", "IND_BL_001", "IND_BL_002"
}

class DocumentRuleValidator:
    @staticmethod
    def validate(document_data: Dict[str, Any], ocr_data: Dict[str, Any], mrz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs deterministic rule checks across document attributes."""
        rules_passed = []
        rules_failed = []
        
        today = date.today()
        fields = ocr_data.get("fields", {})
        mrz_fields = mrz_data.get("fields", {})
        
        # 1. Expiry Check
        exp_str = fields.get("expiryDate") or mrz_fields.get("expiryDate")
        if exp_str:
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                if exp_date < today:
                    rules_failed.append(f"DOCUMENT_EXPIRED: Expired on {exp_str}")
                else:
                    rules_passed.append("EXPIRY_VALID: Document is within validity period")
            except ValueError:
                rules_failed.append(f"INVALID_EXPIRY_FORMAT: {exp_str}")
        else:
            rules_failed.append("MISSING_EXPIRY_DATE: Expiry date not found")
            
        # 2. Date of Birth Check
        dob_str = fields.get("dateOfBirth") or mrz_fields.get("dateOfBirth")
        if dob_str:
            try:
                dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()
                if dob_date > today:
                    rules_failed.append(f"INVALID_DOB_FUTURE: Date of birth {dob_str} is in the future")
                elif (today.year - dob_date.year) > 120:
                    rules_failed.append(f"INVALID_DOB_RANGE: Age exceeds human limit ({today.year - dob_date.year} yrs)")
                else:
                    rules_passed.append("DOB_VALID: Date of birth is valid")
            except ValueError:
                rules_failed.append(f"INVALID_DOB_FORMAT: {dob_str}")
                
        # 3. MRZ Checksum Integrity
        if mrz_data.get("mrzDetected", False):
            if mrz_data.get("mrzValid", False):
                rules_passed.append("MRZ_CHECKSUM_VALID: All ICAO 9303 check digits verified")
            else:
                checks = mrz_data.get("checks", {})
                failed_checks = [k for k, v in checks.items() if not v]
                rules_failed.append(f"MRZ_CHECKSUM_FAILED: Invalid check digits on {', '.join(failed_checks) if failed_checks else 'composite'}")
        else:
            # For non-MRZ documents (e.g. standard driving licences), note it
            if document_data.get("type") in ("DRIVING_LICENCE", "NATIONAL_ID"):
                rules_passed.append("MRZ_EXEMPT: Non-MRZ document type")
            else:
                rules_failed.append("MRZ_MISSING: Machine readable zone not detected")
            
        # 4. Cross-Zone Integrity (Visual Inspection Zone vs MRZ)
        viz_num = fields.get("documentNumber") or fields.get("passportNumber")
        mrz_num = mrz_fields.get("documentNumber")
        if viz_num and mrz_num:
            if viz_num.strip().upper() == mrz_num.strip().upper():
                rules_passed.append("CROSS_ZONE_MATCH: Document number matches between VIZ and MRZ")
            else:
                rules_failed.append(f"CROSS_ZONE_MISMATCH: VIZ number '{viz_num}' != MRZ number '{mrz_num}'")
                
        # 5. Blacklist / Watchlist Lookup (Mock Data Only)
        doc_num = viz_num or mrz_num
        if doc_num and doc_num.strip().upper() in MOCK_SECURITY_BLACKLIST:
            rules_failed.append(f"SECURITY_WATCHLIST_HIT: Document number {doc_num} is flagged in security database")
        else:
            rules_passed.append("WATCHLIST_CLEAR: No record in security exclusion list")
            
        # 6. Required Fields Completeness
        req_keys = ["documentNumber", "nationality", "dateOfBirth"]
        missing = [k for k in req_keys if not fields.get(k) and not mrz_fields.get(k)]
        if not missing:
            rules_passed.append("MANDATORY_FIELDS_PRESENT: All critical fields present")
        else:
            rules_failed.append(f"MISSING_MANDATORY_FIELDS: Missing {', '.join(missing)}")
            
        return {
            "rulesPassed": rules_passed,
            "rulesFailed": rules_failed,
            "validationStatus": "PASSED" if len(rules_failed) == 0 else "FAILED",
            "passedCount": len(rules_passed),
            "failedCount": len(rules_failed)
        }

class RiskScoringEngine:
    """Weighted Risk Engine combining Rule Validations and ML Probabilities into 0-100 Score."""
    
    WEIGHTS = {
        "WATCHLIST_HIT": 35.0,
        "TAMPERING_HIGH": 30.0,
        "MRZ_CHECKSUM_FAIL": 25.0,
        "CROSS_ZONE_MISMATCH": 20.0,
        "FACE_MISMATCH": 25.0,
        "LIVENESS_SPOOF": 25.0,
        "DOCUMENT_EXPIRED": 20.0,
        "OCR_LOW_CONFIDENCE": 15.0,
        "PHOTO_TAMPERING": 20.0,
        "STAMP_FORGERY": 15.0,
    }
    
    @classmethod
    def calculate_risk(
        cls,
        validation_res: Dict[str, Any],
        tamper_res: Dict[str, Any],
        face_res: Dict[str, Any],
        liveness_res: Dict[str, Any],
        ocr_confidence: float = 0.95
    ) -> Dict[str, Any]:
        
        raw_penalty = 0.0
        reasons = []
        
        # 1. Rule Validation Failures
        failed_rules = validation_res.get("rulesFailed", [])
        for f in failed_rules:
            if "SECURITY_WATCHLIST_HIT" in f:
                raw_penalty += cls.WEIGHTS["WATCHLIST_HIT"]
                reasons.append("Security Exclusion Watchlist Alert")
            elif "MRZ_CHECKSUM_FAILED" in f:
                raw_penalty += cls.WEIGHTS["MRZ_CHECKSUM_FAIL"]
                reasons.append("MRZ Checksum Digit Mismatch (Tampering Signature)")
            elif "CROSS_ZONE_MISMATCH" in f:
                raw_penalty += cls.WEIGHTS["CROSS_ZONE_MISMATCH"]
                reasons.append("Cross-Zone Discrepancy between Printed Text and MRZ")
            elif "DOCUMENT_EXPIRED" in f:
                raw_penalty += cls.WEIGHTS["DOCUMENT_EXPIRED"]
                reasons.append("Document Validity Expired")
            else:
                raw_penalty += 10.0
                reasons.append(f"Validation Rule Violation: {f.split(':')[0]}")
                
        # 2. Tampering Model Score
        t_score = tamper_res.get("tamperingScore", 0.0)
        if t_score >= 0.70:
            raw_penalty += cls.WEIGHTS["TAMPERING_HIGH"]
            reasons.append(f"High Tampering Likelihood ({t_score*100:.1f}%) — Type: {tamper_res.get('tamperType', 'GENERIC')}")
        elif t_score >= 0.45:
            raw_penalty += cls.WEIGHTS["TAMPERING_HIGH"] * 0.6
            reasons.append(f"Moderate Tampering / Compression Anomaly ({t_score*100:.1f}%)")
            
        if tamper_res.get("photoTampering", 0.0) > 0.50:
            raw_penalty += cls.WEIGHTS["PHOTO_TAMPERING"] * 0.7
            reasons.append("Localized Portrait Splicing / Photo Tampering Trace Detected")
            
        if tamper_res.get("stampTampering", 0.0) > 0.50:
            raw_penalty += cls.WEIGHTS["STAMP_FORGERY"] * 0.7
            reasons.append("Stamp Boundary Inconsistency / Suspected Forgery")
            
        # 3. Face Verification Signal
        f_status = face_res.get("faceMatchStatus", "UNKNOWN")
        f_score = face_res.get("faceMatchScore", 0.0)
        if f_status == "MISMATCH":
            raw_penalty += cls.WEIGHTS["FACE_MISMATCH"]
            reasons.append(f"Biometric Face Mismatch (Similarity: {f_score:.2f} < threshold)")
            
        # 4. Face Liveness / Anti-Spoofing
        l_status = liveness_res.get("livenessStatus", "UNKNOWN")
        if l_status == "SPOOF":
            raw_penalty += cls.WEIGHTS["LIVENESS_SPOOF"]
            reasons.append("Biometric Presentation Attack / Spoof Detected")
            
        # 5. Low OCR Confidence
        if ocr_confidence < 0.60:
            raw_penalty += cls.WEIGHTS["OCR_LOW_CONFIDENCE"]
            reasons.append("Degraded OCR Confidence (Severe Image Blur or Occlusion)")
            
        # Scale to 0-100 range
        risk_score = int(min(100, max(0, round(raw_penalty))))
        
        # Determine Risk Level
        if risk_score <= 30:
            risk_level = "LOW"
            recommendation = "ACCEPT"
        elif risk_score <= 60:
            risk_level = "MEDIUM"
            recommendation = "SECONDARY_INSPECTION"
        else:
            risk_level = "HIGH"
            recommendation = "REJECT_AND_ESCALATE"
            
        return {
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "recommendation": recommendation,
            "reasons": reasons,
            "timestamp": datetime.now().isoformat() + "Z"
        }
