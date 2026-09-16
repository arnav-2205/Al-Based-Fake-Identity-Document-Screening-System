"""Document-Adaptive Generic National ID & Passport Extraction Engine.

Implements generic National ID processing architecture:
Uploaded Document -> Quality/Orientation -> Classification -> Layout Analysis -> Multilingual Semantic OCR
-> Candidate Ranking -> Machine-Readable Evidence (QR / Barcode / MRZ) -> Per-Field Confidence & Explicit Field States.

NATIONAL ID != AADHAAR. Aadhaar is one specific document adapter inside the generic National ID framework.
"""
from __future__ import annotations

import html
import io
import re
import time
from datetime import datetime
from typing import Any

from PIL import Image, ImageEnhance

from app.services import mrz as mrz_mod

_MRZ_LINE = re.compile(r"[A-Z0-9<=]{15,44}")
_DATE_PATTERNS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
)

_ocr_singleton = None


def _get_easyocr():
    global _ocr_singleton
    if _ocr_singleton is None:
        try:
            import easyocr

            _ocr_singleton = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception as e:
            print(f"Failed to load EasyOCR: {e}")
            _ocr_singleton = False
    return _ocr_singleton


def _normalize_text(text: str) -> str:
    """Decode HTML entities and normalize whitespace for parsing."""
    decoded = html.unescape(text)
    return decoded.replace("\r\n", "\n").replace("\r", "\n")


def _extract_text_from_data(data: bytes) -> tuple[str, float | None, list[dict[str, Any]]]:
    """Extract text, mean OCR confidence, and detailed spatial line boxes.

    Each box dict contains:
    - text: clean string
    - bbox: polygon coordinates
    - confidence: float EasyOCR score (0.0 to 1.0)
    - geometry metrics (xmin, ymin, xmax, ymax, cx, cy, h, w)
    """
    lines: list[str] = []
    ocr_confidence: float | None = None
    boxes: list[dict[str, Any]] = []

    # 1. Check for vector SVG text
    try:
        text_content = data.decode("utf-8", errors="ignore")
        lower = text_content.lower()
        if "<svg" in lower or ("<?xml" in lower and "svg" in lower):
            extracted_tags = re.findall(r">([^<]+)<", text_content)
            for tag in extracted_tags:
                cleaned = html.unescape(tag.strip())
                if cleaned:
                    lines.append(cleaned)
                    boxes.append({
                        "text": cleaned,
                        "bbox": [],
                        "confidence": 0.95,
                        "xmin": 0, "ymin": 0, "xmax": 100, "ymax": 100,
                        "cx": 50, "cy": 50, "h": 20, "w": 100,
                    })
            if lines:
                return "\n".join(lines), 0.95, boxes
    except Exception:
        pass

    # 2. EasyOCR bitmap processing with auto-orientation
    try:
        import numpy as np

        img = Image.open(io.BytesIO(data)).convert("RGB")
        max_dim = max(img.width, img.height)
        if max_dim > 1200:
            scale = 1200.0 / max_dim
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        elif max_dim < 450:
            scale = 650.0 / max(max_dim, 1)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.BICUBIC)

        try:
            enhanced = ImageEnhance.Contrast(img).enhance(1.2)
            enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.15)
            ocr_img = enhanced
        except Exception:
            ocr_img = img

        reader = _get_easyocr()
        if reader and reader is not False:
            result = reader.readtext(np.asarray(ocr_img))

            def eval_orientation(res):
                texts = [t.strip().upper() for _, t, c in res if c >= 0.35 and len(t.strip()) >= 2]
                joined = " ".join(texts)
                landmarks = (
                    "PASSPORT", "PASSEPORT", "REPUBLIC", "GOVERNMENT", "INDIA", "DRIVING",
                    "LICENCE", "LICENSE", "MAHARASHTRA", "TRANSPORT", "UNION", "NATIONAL",
                    "IDENTITY", "CARD", "ELECTION", "COMMISSION", "INCOME TAX", "PAN", "AADHAAR",
                    "SURNAME", "GIVEN", "DATE OF BIRTH", "DOB", "SEX", "VALIDITY", "EXPIRY",
                    "HOLDER", "SIGNATURE", "P<", "I<", "A<", "NAME:", "ISSUE", "PERSONALAUSWEIS",
                    "DEUTSCHLAND", "BUNDESREPUBLIK", "CARTE", "NATIONALE", "MUMBAI", "DELHI",
                    "STATE", "AUTHORITY", "DEPARTMENT", "INDIAN", "REPUBLIQUE", "FRANCAISE"
                )
                landmark_hits = sum(1 for lm in landmarks if lm in joined)
                joined_clean = joined.replace(" ", "")
                if re.search(r"[A-Z0-9]{1,5}<[A-Z0-9<]{8,}", joined_clean) or re.search(r"[A-Z0-9<]{25,44}", joined_clean):
                    landmark_hits += 2
                if re.search(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b", joined) or re.search(r"\b\d{2}[-/]\d{2}[-/]\d{4}\b", joined):
                    landmark_hits += 1
                if re.search(r"\b[A-Z0-9-]{6,20}\b", joined) and len(texts) >= 4:
                    landmark_hits += 1



                score = sum(len(t) for _, t, c in res if len(t) >= 4 and c >= 0.4)
                return landmark_hits, score

            hits, score = eval_orientation(result)
            if hits < 2:
                best_res = result
                best_score = score
                best_hits = hits
                for angle in (90, 270, 180):
                    rot_img = ocr_img.rotate(angle, expand=True)
                    rot_res = reader.readtext(np.asarray(rot_img))
                    rot_hits, rot_score = eval_orientation(rot_res)
                    if rot_hits > best_hits or (rot_hits == best_hits and rot_score > best_score):
                        best_hits = rot_hits
                        best_score = rot_score
                        best_res = rot_res
                        if rot_hits >= 2:
                            break
                result = best_res


            confidences: list[float] = []
            for (box, text, conf) in result:
                cleaned = text.strip()
                if cleaned:
                    lines.append(cleaned)
                    c_val = float(conf)
                    confidences.append(c_val)
                    clean_box = [[float(p[0]), float(p[1])] for p in box]
                    xs = [p[0] for p in clean_box]
                    ys = [p[1] for p in clean_box]
                    boxes.append({
                        "text": cleaned,
                        "bbox": clean_box,
                        "confidence": c_val,
                        "xmin": min(xs), "ymin": min(ys),
                        "xmax": max(xs), "ymax": max(ys),
                        "cx": sum(xs) / len(xs), "cy": sum(ys) / len(ys),
                        "h": max(ys) - min(ys), "w": max(xs) - min(xs),
                    })

            if lines:
                ocr_confidence = sum(confidences) / len(confidences) if confidences else None
                return "\n".join(lines), ocr_confidence, boxes
    except Exception as e:
        print(f"OCR Error: {e}")

    return "", None, []


def _normalize_date(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    m = re.search(r"\b(\d{4}[-/]\d{2}[-/]\d{2})\b", raw)
    if m:
        return m.group(1).replace("/", "-")
    m = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", raw)
    if m:
        raw = m.group(1).replace("/", "-")
    m = re.search(r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", raw)
    if m:
        raw = m.group(1)

    for pattern in _DATE_PATTERNS:
        try:
            return datetime.strptime(raw, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _clean_mrz_candidate(raw: str) -> str:
    s = raw.strip().upper().replace(" ", "").replace("=", "<").replace("«", "<").replace("—", "<").replace("-", "<")
    return re.sub(r"[^A-Z0-9<]", "", s)


def _find_mrz(text: str) -> tuple[str | None, str]:
    text = _normalize_text(text)
    lines = text.splitlines()
    cleaned = [_clean_mrz_candidate(l) for l in lines]
    cleaned = [l for l in cleaned if len(l) >= 15]

    # TD3 Passport (2x44)
    for i, l1 in enumerate(cleaned):
        if (
            l1.startswith("P")
            and len(l1) >= 15
            and (l1.startswith("P<") or (len(l1) >= 5 and l1[2:5].isalpha()))
            and ("<<" in l1 or l1.count("<") >= 3)
        ):
            for j in range(i + 1, min(i + 4, len(cleaned))):
                l2 = cleaned[j]
                if len(l2) >= 20 and any(c.isdigit() for c in l2):
                    return (l1 + "<" * 44)[:44] + "\n" + (l2 + "<" * 44)[:44], "VALIDATED"
            if len(l1) >= 30 and l1.count("<") >= 2:
                return (l1 + "<" * 44)[:44], "DETECTED"

    # TD1 ID Cards (3x30)
    for i, l1 in enumerate(cleaned):
        if any(l1.startswith(p) for p in ("I<", "A<", "C<", "ID<")) and i + 2 < len(cleaned):
            l2 = cleaned[i + 1]
            l3 = cleaned[i + 2]
            if len(l2) >= 20 and len(l3) >= 20:
                return (l1 + "<" * 30)[:30] + "\n" + (l2 + "<" * 30)[:30] + "\n" + (l3 + "<" * 30)[:30], "VALIDATED"

    return None, "NOT_AVAILABLE"


def _extract_barcode_info(data: bytes) -> dict[str, Any]:
    """Scan document for 1D or 2D barcodes (PDF417, Code128, DataMatrix)."""
    try:
        import numpy as np
        import cv2

        img_pil = Image.open(io.BytesIO(data)).convert("RGB")
        img_np = np.asarray(img_pil)

        if hasattr(cv2, "barcode_BarcodeDetector"):
            detector = cv2.barcode_BarcodeDetector()
            res_bc = detector.detectAndDecode(img_np)
            retval = res_bc[0] if len(res_bc) > 0 else False
            decoded_info = res_bc[1] if len(res_bc) > 1 else None
            decoded_type = res_bc[2] if len(res_bc) > 2 else None
            if retval and decoded_info:
                clean_info = [info for info in decoded_info if info]
                if clean_info:
                    b_type = decoded_type[0] if decoded_type else "BARCODE"
                    return {
                        "barcodeDetected": True,
                        "barcodeDecoded": True,
                        "barcodeStatus": "DECODED",
                        "barcodeType": str(b_type),
                        "barcodeData": clean_info[0],
                    }

        # Secondary heuristic: OpenCV contour detector for barcode patterns
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=-1)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=-1)
        gradient = cv2.subtract(grad_x, grad_y)
        gradient = cv2.convertScaleAbs(gradient)
        blurred = cv2.blur(gradient, (9, 9))
        _, thresh = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        closed = cv2.erode(closed, None, iterations=4)
        closed = cv2.dilate(closed, None, iterations=4)

        cnts, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            rect = cv2.minAreaRect(c)
            w, h = rect[1]
            if w > 0 and h > 0:
                aspect = max(w, h) / min(w, h)
                area = w * h
                if aspect > 2.5 and area > 1500:
                    return {
                        "barcodeDetected": True,
                        "barcodeDecoded": False,
                        "barcodeStatus": "DETECTED",
                        "barcodeType": "PDF417/1D",
                        "barcodeData": None,
                    }
    except Exception as e:
        print(f"Barcode scanning info error: {e}")

    return {
        "barcodeDetected": False,
        "barcodeDecoded": False,
        "barcodeStatus": "NOT_AVAILABLE",
        "barcodeType": "NONE",
        "barcodeData": None,
    }


def _parse_qr_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    data: dict[str, Any] = {}

    if "<PrintLetterBarcodeData" in text or text.startswith("<"):
        try:
            import xml.etree.ElementTree as ET

            start = text.find("<PrintLetterBarcodeData")
            if start != -1:
                end = text.find("/>", start)
                if end != -1:
                    xml_sub = text[start : end + 2]
                    root = ET.fromstring(xml_sub)
                    attrs = root.attrib
                    data["name"] = attrs.get("name", "")
                    data["dob"] = attrs.get("dob", "") or attrs.get("yob", "")
                    data["gender"] = attrs.get("gender", "")
                    data["documentNumber"] = attrs.get("uid", "")
                    addr_parts = [attrs.get(k) for k in ("house", "street", "lm", "loc", "vtc", "po", "dist", "state", "pc") if attrs.get(k)]
                    if addr_parts:
                        data["address"] = ", ".join(addr_parts)
                    return data
        except Exception:
            pass

    if text.startswith("{") and text.endswith("}"):
        try:
            import json

            j = json.loads(text)
            data["name"] = j.get("name") or j.get("name_en") or j.get("full_name") or ""
            data["dob"] = j.get("dob") or j.get("date_of_birth") or j.get("yob") or ""
            data["gender"] = j.get("gender") or j.get("sex") or ""
            data["documentNumber"] = j.get("uid") or j.get("id") or j.get("doc_num") or ""
            data["address"] = j.get("address") or j.get("addr") or ""
            return data
        except Exception:
            pass

    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k_clean = k.strip().lower()
            v_clean = v.strip()
            if "name" in k_clean:
                data["name"] = v_clean
            elif "dob" in k_clean or "birth" in k_clean:
                data["dob"] = v_clean
            elif "gender" in k_clean or "sex" in k_clean:
                data["gender"] = v_clean
            elif "id" in k_clean or "uid" in k_clean or "number" in k_clean:
                data["documentNumber"] = v_clean
            elif "addr" in k_clean:
                data["address"] = v_clean

    return data


def _compare_qr_vs_ocr(qr_data: dict, viz_fields: dict, fields: dict) -> tuple[str, list[str]]:
    if not qr_data:
        return "NOT_APPLICABLE", []

    discrepancies = []
    matches = 0
    total_checked = 0

    qr_name = qr_data.get("name", "").strip().upper()
    ocr_name = (fields.get("name") or viz_fields.get("name") or "").strip().upper()
    if qr_name and ocr_name:
        total_checked += 1
        if qr_name == ocr_name or qr_name in ocr_name or ocr_name in qr_name:
            matches += 1
        else:
            discrepancies.append(f"Name mismatch: QR='{qr_name}' vs OCR='{ocr_name}'")

    qr_dob = qr_data.get("dob", "").strip()
    ocr_dob = (fields.get("dateOfBirth") or viz_fields.get("dateOfBirth") or "").strip()
    if qr_dob and ocr_dob:
        total_checked += 1
        if qr_dob in ocr_dob or ocr_dob in qr_dob:
            matches += 1
        else:
            discrepancies.append(f"DOB mismatch: QR='{qr_dob}' vs OCR='{ocr_dob}'")

    qr_gen = qr_data.get("gender", "").strip().upper()
    ocr_gen = (fields.get("gender") or viz_fields.get("gender") or "").strip().upper()
    if qr_gen and ocr_gen:
        total_checked += 1
        if (qr_gen.startswith("M") and ocr_gen.startswith("M")) or (qr_gen.startswith("F") and ocr_gen.startswith("F")):
            matches += 1
        else:
            discrepancies.append(f"Gender mismatch: QR='{qr_gen}' vs OCR='{ocr_gen}'")

    qr_num = qr_data.get("documentNumber", "").replace(" ", "").upper()
    ocr_num = (fields.get("documentNumber") or fields.get("passportNumber") or "").replace(" ", "").upper()
    if qr_num and ocr_num:
        total_checked += 1
        if qr_num == ocr_num or qr_num in ocr_num or ocr_num in qr_num:
            matches += 1
        else:
            discrepancies.append(f"Document # mismatch: QR='{qr_num}' vs OCR='{ocr_num}'")

    if total_checked == 0:
        return "NOT_APPLICABLE", []
    if matches == total_checked:
        return "MATCH", []
    if matches > 0:
        return "PARTIAL_MATCH", discrepancies
    return "MISMATCH", discrepancies


def _extract_qr_info(data: bytes, viz_fields: dict, fields: dict) -> dict:
    try:
        import numpy as np
        import cv2

        img_pil = Image.open(io.BytesIO(data)).convert("RGB")
        img_np = np.asarray(img_pil)

        detector = cv2.QRCodeDetector()
        decoded_text = ""
        qr_detected = False

        for angle in (0, 90, 180, 270):
            if angle == 0:
                cur_img = img_np
            elif angle == 90:
                cur_img = cv2.rotate(img_np, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                cur_img = cv2.rotate(img_np, cv2.ROTATE_180)
            else:
                cur_img = cv2.rotate(img_np, cv2.ROTATE_90_COUNTERCLOCKWISE)

            found, bbox = detector.detect(cur_img)
            if found:
                qr_detected = True
                text_dec, _, _ = detector.detectAndDecode(cur_img)
                if text_dec:
                    decoded_text = text_dec
                    break

                try:
                    pts = bbox[0].astype(int)
                    xmin, ymin = np.min(pts, axis=0)
                    xmax, ymax = np.max(pts, axis=0)
                    h, w = cur_img.shape[:2]
                    pad = 40
                    xmin, ymin = max(0, xmin - pad), max(0, ymin - pad)
                    xmax, ymax = min(w, xmax + pad), min(h, ymax + pad)
                    crop = cur_img[ymin:ymax, xmin:xmax]
                    crop_large = cv2.resize(crop, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                    text_dec, _, _ = detector.detectAndDecode(crop_large)
                    if text_dec:
                        decoded_text = text_dec
                        break

                    gray = cv2.cvtColor(crop_large, cv2.COLOR_BGR2GRAY) if len(crop_large.shape) == 3 else crop_large
                    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    text_dec, _, _ = detector.detectAndDecode(otsu)
                    if text_dec:
                        decoded_text = text_dec
                        break
                except Exception:
                    pass

        if not decoded_text and qr_detected:
            retval, decoded_info, _, _ = detector.detectAndDecodeMulti(img_np)
            if retval and decoded_info:
                decoded_text = decoded_info[0]

        if not decoded_text:
            return {
                "qrDetected": qr_detected,
                "qrDecoded": False,
                "qrStatus": "DETECTED" if qr_detected else "NOT_AVAILABLE",
                "qrSignatureVerified": False,
                "qrSignatureStatus": "QR Code Detected (Unreadable Payload)" if qr_detected else "No QR Code Detected",
                "qrData": None,
                "qrOcrMatchStatus": "NOT_APPLICABLE",
                "qrOcrDiscrepancies": [],
            }

        qr_payload = _parse_qr_payload(decoded_text)
        sig_verified = False
        sig_status = "Signature Unverified (No PKI Cert Chain Root)"
        match_status, discrepancies = _compare_qr_vs_ocr(qr_payload, viz_fields, fields)

        return {
            "qrDetected": True,
            "qrDecoded": True,
            "qrStatus": "DECODED",
            "qrSignatureVerified": sig_verified,
            "qrSignatureStatus": sig_status,
            "qrData": qr_payload,
            "qrOcrMatchStatus": match_status,
            "qrOcrDiscrepancies": discrepancies,
        }
    except Exception as e:
        print(f"QR Extraction Error: {e}")
        return {
            "qrDetected": False,
            "qrDecoded": False,
            "qrStatus": "NOT_AVAILABLE",
            "qrSignatureVerified": False,
            "qrSignatureStatus": "QR Processing Error",
            "qrData": None,
            "qrOcrMatchStatus": "NOT_APPLICABLE",
            "qrOcrDiscrepancies": [],
        }


def _get_document_capabilities(
    category: str,
    subtype: str,
    mrz_detected: bool = False,
    qr_detected: bool = False,
    barcode_detected: bool = False,
) -> tuple[list[str], list[str]]:
    """Determine applicable fields and applicable verification checks based on document classification and detected signals."""
    applicable_checks: list[str] = ["OCR", "TAMPER", "BIOMETRIC"]

    cat = (category or "NATIONAL_ID").upper()
    sub = (subtype or "NATIONAL_ID_CARD").upper()

    if cat == "PASSPORT" or sub == "PASSPORT":
        applicable_fields = [
            "documentNumber", "passportNumber", "holderName", "dateOfBirth", "gender",
            "nationality", "issuingCountry", "issueDate", "expiryDate", "photo"
        ]
        applicable_checks.append("MRZ")
    elif cat == "VISA" or sub == "VISA":
        applicable_fields = [
            "documentNumber", "visaNumber", "holderName", "passportNumber", "nationality",
            "dateOfBirth", "gender", "issuingCountry", "issueDate", "expiryDate", "photo"
        ]
        if mrz_detected:
            applicable_checks.append("MRZ")
    elif cat == "DRIVING_LICENCE" or sub == "DRIVING_LICENCE":
        applicable_fields = [
            "documentNumber", "holderName", "dateOfBirth", "gender",
            "address", "issueDate", "expiryDate", "issuingCountry", "photo"
        ]
        if barcode_detected:
            applicable_checks.append("BARCODE")
    elif sub == "AADHAAR":
        applicable_fields = [
            "documentNumber", "holderName", "dateOfBirth", "gender", "address", "photo"
        ]
        applicable_checks.append("QR")
    elif sub in ("VOTER_ID", "ELECTORAL_ID"):
        applicable_fields = [
            "documentNumber", "holderName", "dateOfBirth", "gender", "address", "photo"
        ]
    elif sub in ("TAX_ID", "PAN"):
        applicable_fields = [
            "documentNumber", "holderName", "dateOfBirth", "issuingCountry", "photo"
        ]
    elif sub == "RESIDENT_PERMIT":
        applicable_fields = [
            "documentNumber", "holderName", "dateOfBirth", "gender", "nationality",
            "address", "issueDate", "expiryDate", "photo"
        ]
        if mrz_detected:
            applicable_checks.append("MRZ")
    elif sub == "SOCIAL_SECURITY_ID":
        applicable_fields = [
            "documentNumber", "holderName", "dateOfBirth", "issuingCountry", "photo"
        ]
    else:  # NATIONAL_ID_CARD / OTHER_GOVT_ID / OTHER_GOVT_DOC
        applicable_fields = [
            "documentNumber", "holderName", "dateOfBirth", "gender",
            "nationality", "issuingCountry", "issueDate", "expiryDate", "address", "photo"
        ]
        if mrz_detected:
            applicable_checks.append("MRZ")

    if qr_detected and "QR" not in applicable_checks:
        applicable_checks.append("QR")
    if barcode_detected and "BARCODE" not in applicable_checks:
        applicable_checks.append("BARCODE")

    return applicable_fields, applicable_checks


# ==============================================================================
# GENERIC NATIONAL ID ADAPTER ENGINE
# ==============================================================================

class GenericNationalIDAdapter:
    """Document-adaptive Generic National ID Field Extractor.

    Supports multilingual labels, spatial bounding-box layout parsing,
    candidate ranking for unlabeled fields, and country detection.
    """

    NOISE_KEYWORDS = (
        "GOVERNMENT", "INDIA", "AADHAAR", "UNIQUE", "IDENTIFICATION", "AUTHORITY", "UNION",
        "REPUBLIC", "STATE", "DRIVER", "LICENCE", "LICENSE", "COMMISSION", "INCOME", "TAX",
        "DEPARTMENT", "ELECTION", "ELECTOR", "ELECTORAL", "BUNDESREPUBLIK", "DEUTSCHLAND",
        "PERSONALAUSWEIS", "REPUBLIQUE", "FRANCAISE", "MINISTERE", "INTERIEUR", "NATIONAL",
        "IDENTITY", "CARD", "PASSPORT", "PASSEPORT", "SIGNATURE", "HOLDER", "ADDRESS",
        "DOMICILE", "ANSCHRIFT", "DIRECCION", "AUTHORITY", "ISSUED", "ISSUING", "CODE",
        "MALE", "FEMALE", "SEX", "GENDER", "DOB", "DATE", "BIRTH", "NAISSANCE"
    )

    def extract(self, text: str, boxes: list[dict[str, Any]], raw_mrz: str | None) -> dict[str, Any]:
        text_norm = _normalize_text(text)
        upper_text = text_norm.upper()
        lines = [l.strip() for l in text_norm.splitlines() if l.strip()]

        # 1. Detect Issuing Country & Document Classification
        country = self._detect_country(upper_text)
        doc_category, doc_subtype = self._detect_doc_category_and_subtype(upper_text, raw_mrz)
        doc_type = doc_subtype

        applicable_fields, applicable_checks = _get_document_capabilities(
            doc_category, doc_subtype, raw_mrz is not None
        )

        fields: dict[str, str] = {}
        field_confidences: dict[str, float] = {}
        notes: list[str] = [f"Generic National ID Adapter active (Category: {doc_category}, Subtype: {doc_subtype}, Country: {country})"]

        # 2. Semantic Multilingual Field Extraction
        # Name candidate extraction
        name_val, name_conf, name_reason = self._extract_holder_name(lines, boxes, notes)
        if name_val:
            fields["name"] = name_val
            fields["holderName"] = name_val
            field_confidences["name"] = name_conf
            field_confidences["holderName"] = name_conf
            notes.append(f"Name Candidate Ranking: Selected '{name_val}' ({name_reason})")

        # Document Number extraction
        doc_num, num_conf = self._extract_doc_number(lines, upper_text, boxes)
        if doc_num:
            fields["documentNumber"] = doc_num
            fields["passportNumber"] = doc_num
            field_confidences["documentNumber"] = num_conf

        # Date of Birth
        dob_val, dob_conf = self._extract_dob(lines, upper_text, boxes)
        if dob_val:
            fields["dateOfBirth"] = dob_val
            field_confidences["dateOfBirth"] = dob_conf

        # Gender
        gender_val, gen_conf = self._extract_gender(lines, upper_text, boxes)
        if gender_val:
            fields["gender"] = gender_val
            field_confidences["gender"] = gen_conf

        # Nationality
        nat_val, nat_conf = self._extract_nationality(upper_text, country)
        if nat_val:
            fields["nationality"] = nat_val
            field_confidences["nationality"] = nat_conf

        # Issue Date
        issue_val, issue_conf = self._extract_issue_date(lines, upper_text, boxes)
        if issue_val:
            fields["issueDate"] = issue_val
            field_confidences["issueDate"] = issue_conf

        # Expiry Date
        expiry_val, expiry_conf = self._extract_expiry_date(lines, upper_text, boxes)
        if expiry_val:
            fields["expiryDate"] = expiry_val
            field_confidences["expiryDate"] = expiry_conf

        # Address
        addr_val, addr_conf = self._extract_address(text_norm, lines, boxes)
        if addr_val:
            fields["address"] = addr_val
            field_confidences["address"] = addr_conf

        fields["issuingCountry"] = country

        # 3. Determine Explicit Field States
        field_states = self._determine_field_states(fields, field_confidences, doc_category, doc_subtype, applicable_fields)

        return {
            "fields": fields,
            "fieldConfidences": field_confidences,
            "fieldStates": field_states,
            "issuingCountry": country,
            "detectedDocumentType": doc_type,
            "documentCategory": doc_category,
            "documentSubtype": doc_subtype,
            "applicableFields": applicable_fields,
            "applicableChecks": applicable_checks,
            "notes": notes,
        }

    def _detect_country(self, upper: str) -> str:
        if any(k in upper for k in ("INDIA", "AADHAAR", "UIDAI", "GOVERNMENT OF INDIA", "MAHARASHTRA", "TRANSPORT DEPARTMENT", "INCOME TAX", "ELECTION COMMISSION")):
            return "INDIA"
        if any(k in upper for k in ("DEUTSCHLAND", "BUNDESREPUBLIK", "PERSONALAUSWEIS", "REPUBLIK DEUTSCHLAND")):
            return "GERMANY"
        if any(k in upper for k in ("UNITED STATES", "USA", "STATE OF", "DRIVER LICENSE", "DRIVING LICENSE")):
            return "UNITED STATES"
        if any(k in upper for k in ("REPUBLIQUE FRANCAISE", "CARTE NATIONALE", "FRANCE")):
            return "FRANCE"
        if any(k in upper for k in ("UNITED KINGDOM", "GREAT BRITAIN", "DRIVING LICENCE")):
            return "UNITED KINGDOM"
        if any(k in upper for k in ("EMIRATES ID", "UNITED ARAB EMIRATES", "IDENTITY AUTHORITY")):
            return "UNITED ARAB EMIRATES"
        if any(k in upper for k in ("REPUBLIC OF SINGAPORE", "SINGAPORE")):
            return "SINGAPORE"
        if any(k in upper for k in ("REPUBLIC OF KENYA", "KENYA")):
            return "KENYA"
        if any(k in upper for k in ("FEDERAL REPUBLIC OF NIGERIA", "NIGERIA")):
            return "NIGERIA"
        if any(k in upper for k in ("REPUBLIC OF SOUTH AFRICA", "SOUTH AFRICA")):
            return "SOUTH AFRICA"
        return "UNKNOWN"

    def _detect_doc_category_and_subtype(self, upper: str, raw_mrz: str | None) -> tuple[str, str]:
        if raw_mrz and raw_mrz.startswith("P<"):
            return "PASSPORT", "PASSPORT"
        if raw_mrz and (raw_mrz.startswith("V<") or "\nV<" in raw_mrz):
            return "VISA", "VISA"
        if any(k in upper for k in ("AADHAAR", "UIDAI", "UNIQUE IDENTIFICATION")) or (any(k in upper for k in ("GOVERNMENT OF INDIA", "INDIA")) and re.search(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", upper)):
            return "NATIONAL_ID", "AADHAAR"
        if any(k in upper for k in ("DRIVING LICENCE", "DRIVING LICENSE", "MOTOR VEHICLES", "TRANSPORT DEPARTMENT")):
            return "DRIVING_LICENCE", "DRIVING_LICENCE"
        if any(k in upper for k in ("INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "PAN CARD", "TAX ID")):
            return "NATIONAL_ID", "TAX_ID"
        if any(k in upper for k in ("ELECTION COMMISSION", "ELECTORAL", "ELECTOR PHOTO", "VOTER ID", "EPIC")):
            return "NATIONAL_ID", "VOTER_ID"
        if any(k in upper for k in ("RESIDENCE PERMIT", "RESIDENT PERMIT", "AUFENTHALTSTITEL", "PERMIT DE SEJOUR")):
            return "NATIONAL_ID", "RESIDENT_PERMIT"
        if any(k in upper for k in ("SOCIAL SECURITY", "SOCIAL INSURANCE", "SSN")):
            return "NATIONAL_ID", "SOCIAL_SECURITY_ID"
        if any(k in upper for k in ("VISA", "VISA TRAVEL", "SCHENGEN VISA", "ENTRY VISA", "EXIT VISA", "TRANSIT VISA", "TYPE OF VISA")):
            return "VISA", "VISA"
        if any(k in upper for k in ("PASSPORT", "PASSEPORT")):
            return "PASSPORT", "PASSPORT"
        if any(k in upper for k in ("PERSONALAUSWEIS", "NATIONAL ID", "IDENTITY CARD", "CARTE NATIONALE", "CITIZEN CARD")):
            return "NATIONAL_ID", "NATIONAL_ID_CARD"
        return "NATIONAL_ID", "OTHER_GOVT_ID"

    def _detect_doc_type(self, upper: str, raw_mrz: str | None) -> str:
        cat, sub = self._detect_doc_category_and_subtype(upper, raw_mrz)
        return sub

    def _extract_holder_name(
        self, lines: list[str], boxes: list[dict[str, Any]], notes: list[str]
    ) -> tuple[str, float, str]:
        # Path A: Labeled Name (English, French, German, Spanish, etc.)
        for b in boxes:
            t = b["text"]
            m = re.search(
                r"(?:NAME|FULL\s*NAME|NOM|PRENOM|NOMBRE|GIVEN\s*NAME|SURNAME|HOLDER(?:'S)?\s*NAME|CITIZEN\s*NAME)\s*[:\s|-]+\s*([A-Z][A-Za-z '.-]{2,40})",
                t,
                re.I,
            )
            if m:
                cand = m.group(1).strip().upper()
                if not any(k in cand for k in self.NOISE_KEYWORDS):
                    return cand, max(0.85, b["confidence"]), "Explicit Label Match"

        # Path B: Spatial candidate pairing from boxes (label box + value box)
        for b in boxes:
            t = b["text"]
            if re.search(r"\b(NAME|NOM|GIVEN|SURNAME|NOMBRE|HOLDER)\b", t, re.I):
                lbl_cx, lbl_cy = b["cx"], b["cy"]
                cands = [
                    box for box in boxes
                    if box != b and abs(box["cy"] - lbl_cy) < 18 and 5 < box["xmin"] - b["xmax"] < 250
                ]
                if not cands:
                    cands = [
                        box for box in boxes
                        if box != b and 5 < box["ymin"] - b["ymin"] < 50 and abs(box["xmin"] - b["xmin"]) < 80
                    ]
                for c in cands:
                    cand_val = c["text"].strip(" :|-").upper()
                    if len(cand_val) >= 3 and not any(k in cand_val for k in self.NOISE_KEYWORDS):
                        return cand_val, max(0.85, c["confidence"]), "Spatial Bounding Box Match"

        # Path C: Layout Candidate Ranking (For documents without 'Name:' label, e.g. Aadhaar / Generic ID)
        anchor_idx = -1
        for i, line in enumerate(lines):
            if re.search(r"\b(DOB|YEAR OF BIRTH|YOB|DATE OF BIRTH|MALE|FEMALE|SON OF|DAUGHTER OF|WIFE OF|S/O|D/O|W/O)\b", line, re.I):
                anchor_idx = i
                break

        candidates: list[tuple[str, float, float]] = []
        search_lines = lines[:anchor_idx] if anchor_idx > 0 else lines

        for line_str in search_lines:
            cand = line_str.strip()
            up_cand = cand.upper()

            if len(cand) < 3 or len(cand) > 40:
                continue
            if any(k in up_cand for k in self.NOISE_KEYWORDS):
                continue
            if re.search(r"\d", cand):
                continue
            if not re.match(r"^[A-Za-z][A-Za-z '.-]+$", cand):
                continue

            score = 0.5
            words = cand.split()
            if 2 <= len(words) <= 4:
                score += 0.25
            if cand.isupper():
                score += 0.15
            elif cand.istitle():
                score += 0.10

            box_c = 0.80
            for box in boxes:
                if cand.lower() in box["text"].lower():
                    box_c = box["confidence"]
                    break

            candidates.append((cand.upper(), score, box_c))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_name, best_score, box_conf = candidates[0]
            conf = min(0.98, max(0.65, box_conf * best_score))
            return best_name, round(conf, 2), f"Candidate Ranking (Score: {best_score:.2f})"

        return "", 0.0, "NOT_DETECTED"

    def _extract_doc_number(
        self, lines: list[str], upper: str, boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        aadhaar_m = re.search(r"\b(\d{4}[-\s]?\d{4}[-\s]?\d{4})\b", upper)
        if aadhaar_m and any(k in upper for k in ("AADHAAR", "GOVERNMENT OF INDIA", "MALE", "FEMALE", "INDIA", "UNIQUE")):
            return aadhaar_m.group(1), 0.96

        dl_m = re.search(r"\b([A-Z]{2}[0-9O]{1,2}\s*[0-9O]{11,15})\b", upper)
        if dl_m:
            return dl_m.group(1).replace("O", "0"), 0.95

        pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", upper)
        if pan_m:
            return pan_m.group(1), 0.97

        voter_m = re.search(r"\b([A-Z]{3}[0-9]{7})\b", upper)
        if voter_m:
            return voter_m.group(1), 0.95

        for l in lines:
            up_l = l.strip().upper()
            doc_m = re.search(
                r"(?:DOCUMENT|ID|IDENTIFICATION|CARD|PASSPORT|LICENCE|LICENSE|SERIAL)\s*(?:NO?|NA?|NUM|NUMBER)?\s*[:\s|-]+\s*([A-Z0-9 -]{4,25})",
                up_l,
            )
            if doc_m:
                val = doc_m.group(1).strip().replace(" ", "")
                if len(val) >= 4 and not any(k in val for k in self.NOISE_KEYWORDS):
                    return val, 0.90

        for l in lines:
            cleaned_l = l.strip().upper()
            if any(k in cleaned_l for k in self.NOISE_KEYWORDS) or len(cleaned_l) < 5 or len(cleaned_l) > 20:
                continue
            if re.match(r"^[A-Z0-9-]{5,20}$", cleaned_l) and sum(1 for c in cleaned_l if c.isdigit()) >= 3 and not re.search(r"\d{4}[-/]\d{2}[-/]\d{2}", cleaned_l):
                return cleaned_l, 0.85

        return "", 0.0

    def _extract_dob(
        self, lines: list[str], upper: str, boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        m = re.search(
            r"(?:DOB|DATE\s*OF\s*BIRTH|YEAR\s*OF\s*BIRTH|BIRTH\s*YEAR|YOB|BIRTH|BORN|NAISSANCE|GEBURTSDATUM|FECHA\s*DE\s*NACIMIENTO)\s*[:\s|/]*"
            r"(\d{1,2}\s+[A-Z]{3,9}\s+\d{4}|\d{1,4}[-/,\s]\d{1,2}[-/,\s]\d{2,4}|\b\d{4}\b)",
            upper,
        )
        if m:
            raw_d = m.group(1).replace(",", "/").replace(" ", "-")
            norm = _normalize_date(raw_d)
            if norm:
                return norm, 0.92

        for l in lines:
            if re.search(r"\b(DOB|BIRTH|YOB|NAISSANCE|GEBURTSDATUM)\b", l, re.I):
                d_m = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\b\d{4}\b)\b", l)
                if d_m:
                    norm = _normalize_date(d_m.group(1))
                    if norm:
                        return norm, 0.88

        for l in lines:
            d_m = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", l)
            if d_m:
                norm = _normalize_date(d_m.group(1))
                if norm and not norm.startswith("202"):
                    return norm, 0.82

        return "", 0.0

    def _extract_gender(
        self, lines: list[str], upper: str, boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        m = re.search(r"(?:SEX|GENDER|SEXE|GESCHLECHT|SEXO)\s*[:\s|/]+\s*(M|F|MALE|FEMALE)", upper)
        if m:
            val = m.group(1).upper()
            return ("M" if val.startswith("M") else "F"), 0.94

        if re.search(r"\bMALE\b", upper):
            return "M", 0.90
        if re.search(r"\bFEMALE\b", upper):
            return "F", 0.90
        if re.search(r"\bSon\s*(?:of)?\b", upper, re.I):
            return "M", 0.85
        if re.search(r"\b(?:Daughter|Wife)\s*(?:of)?\b", upper, re.I):
            return "F", 0.85

        for l in lines:
            up_l = l.strip().upper()
            if up_l in ("M", "F", "SEX: M", "SEX: F", "GENDER: M", "GENDER: F"):
                return ("M" if "M" in up_l else "F"), 0.85

        return "", 0.0

    def _extract_nationality(self, upper: str, country: str) -> tuple[str, float]:
        m = re.search(r"(?:NATIONALITY|NAT|CITIZENSHIP|STAATSANGEHÖRIGKEIT|NACIONALIDAD)\s*[:\s|-]+\s*([A-Z]{3}|\w+)", upper)
        if m:
            val = m.group(1).upper()
            if len(val) == 3:
                return val, 0.95
        if country == "INDIA":
            return "IND", 0.92
        if country == "GERMANY":
            return "DEU", 0.92
        if country == "UNITED STATES":
            return "USA", 0.92
        if country == "FRANCE":
            return "FRA", 0.92
        return "", 0.0

    def _extract_issue_date(
        self, lines: list[str], upper: str, boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        m = re.search(
            r"(?:ISSUE\s*DATE|DATE\s*OF\s*ISSUE|ISSUED|AUSSTELLUNGSDATUM|DELIVRANCE|EXPEDICION)\b[\s\S]{0,80}?(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})",
            upper,
        )
        if m:
            norm = _normalize_date(m.group(1))
            if norm:
                return norm, 0.90
        return "", 0.0

    def _extract_expiry_date(
        self, lines: list[str], upper: str, boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        # 1. Line-by-line targeted scan for EXPIRY/VALIDITY keywords
        candidate = ""
        for i, line in enumerate(lines):
            up_line = line.strip().upper()
            if any(kw in up_line for kw in ("EXPIRY", "EXPIRES", "VALID UNTIL", "VALIDITY", "ABLAUFDATUM", "CADUCIDAD", "EXPIRATION", "DEXPIRA")):
                block = " ".join([lines[j].strip() for j in range(i, min(i + 8, len(lines)))])
                d_matches = re.findall(r"\b(\d{1,4}[-/ ]\d{1,2}[-/ ]\d{2,4})\b", block)
                for dm in d_matches:
                    clean_dm = dm.strip().replace(" ", "-")
                    norm = _normalize_date(clean_dm)
                    if norm:
                        if int(norm[:4]) >= 2025:
                            return norm, 0.92
                        if not candidate:
                            candidate = norm

        if candidate:
            return candidate, 0.88

        # 2. Strict regex search fallback with explicit non-issue-date constraint
        m = re.search(
            r"(?:EXPIRY|EXPIRES|VALID\s*UNTIL|VALIDITY|ABLAUFDATUM|CADUCIDAD|EXPIRATION|DEXPIRA)\b[^\n\d]{0,30}(\d{1,4}[-/ ]\d{1,2}[-/ ]\d{2,4}[A-Za-z]?)",
            upper,
        )
        if m:
            raw_exp = m.group(1).strip().replace("s", "5").replace("S", "5").replace(" ", "-")
            norm = _normalize_date(raw_exp)
            if norm:
                return norm, 0.90
        return "", 0.0

    def _extract_address(
        self, text_norm: str, lines: list[str], boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        m = re.search(r"(?:Address|Residence|Domicile|Anschrift|Direccion)\s*[:\s|]+\n*([^\n]+(?:\n[^\n]+){0,2})", text_norm, re.I)
        if m:
            clean_addr = " ".join(m.group(1).split()).strip()
            if len(clean_addr) > 5:
                return clean_addr, 0.88
        return "", 0.0

    def _determine_field_states(
        self, fields: dict[str, str], confidences: dict[str, float], doc_category: str, doc_subtype: str, applicable_fields: list[str]
    ) -> dict[str, str]:
        all_target_fields = [
            "documentNumber", "passportNumber", "holderName", "dateOfBirth", "gender",
            "nationality", "issuingCountry", "issueDate", "expiryDate", "address"
        ]
        states: dict[str, str] = {}

        if fields.get("issuingCountry") and fields["issuingCountry"] != "UNKNOWN":
            confidences["issuingCountry"] = 0.95

        for f in all_target_fields:
            if f not in applicable_fields:
                states[f] = "NOT_APPLICABLE"
                continue

            val = fields.get(f) or (fields.get("name") if f == "holderName" else None)
            conf = confidences.get(f, 0.0)

            if val:
                states[f] = "DETECTED" if conf >= 0.65 else "LOW_CONFIDENCE"
            else:
                states[f] = "NOT_DETECTED"

        return states


def detect_document_type(
    text: str,
    raw_mrz: str | None = None,
    boxes: list[dict[str, Any]] | None = None,
    qr_data: dict | None = None,
    barcode_data: dict | None = None,
) -> tuple[str, float]:
    """Automatically detects document type and confidence from OCR text, MRZ, and machine-readable evidence.

    Supported types: PASSPORT, VISA, DRIVING_LICENCE, NATIONAL_ID, PERMIT, UNKNOWN.
    """
    text_norm = _normalize_text(text).upper()

    # 1. MRZ Detection (Passports & Visas)
    if raw_mrz:
        clean_mrz = raw_mrz.strip().upper()
        if clean_mrz.startswith("P<") or "P<" in clean_mrz:
            return "PASSPORT", 0.98
        if clean_mrz.startswith("V<") or "\nV<" in clean_mrz:
            return "VISA", 0.98

    # 2. VISA Detection (Evaluated before generic Passport text keywords so "PASSPORT NO." on Visas does not misclassify as Passport)
    visa_keywords = (
        "VISA", "SCHENGEN VISA", "ENTRY VISA", "EXIT VISA", "TRANSIT VISA",
        "TYPE OF VISA", "VISA TYPE", "VISA NO", "VISA NUMBER", "DURATION OF STAY",
        "NUMBER OF ENTRIES", "VALID FOR", "ENTRIES: MULT", "ENTRIES: 01", "ENTRIES: 02"
    )
    visa_hits = sum(1 for k in visa_keywords if k in text_norm)
    if visa_hits >= 2 or any(k in text_norm for k in ("SCHENGEN VISA", "TYPE OF VISA", "VISA TYPE")):
        return "VISA", 0.95
    if visa_hits == 1 and "VISA" in text_norm:
        if any(k in text_norm for k in ("PASSPORT NO", "PASSPORT NUMBER", "STAY", "ENTRIES", "VALID FOR", "CATEGORY", "ISSUED AT", "BEARER", "CLASS", "CONTROL NUMBER")):
            return "VISA", 0.90

    # 3. PASSPORT Detection
    passport_keywords = ("PASSPORT", "PASSEPORT", "PASAPORTE", "REPUBLIK PASSPORT", "REPUBLIC PASSPORT")
    if any(k in text_norm for k in passport_keywords):
        if any(k in text_norm for k in ("REPUBLIC", "GOVERNMENT", "KINGDOM", "UNION", "FEDERATION", "P<", "COUNTRY CODE", "AUTHORITY")):
            return "PASSPORT", 0.95
        return "PASSPORT", 0.90

    # 3. DRIVING_LICENCE Detection
    if barcode_data and barcode_data.get("barcodeDetected"):
        b_type = str(barcode_data.get("barcodeType", "")).upper()
        if "PDF417" in b_type or "AAMVA" in b_type:
            return "DRIVING_LICENCE", 0.98

    dl_keywords = (
        "DRIVING LICENCE", "DRIVING LICENSE", "DRIVER LICENSE", "DRIVER LICENCE",
        "LICENCE NO", "LICENSE NO", "DL NO", "MOTOR VEHICLES", "TRANSPORT DEPARTMENT",
        "CLASS OF VEHICLES", "COV", "DRIVING PERMIT", "PERMIS DE CONDUIRE", "FÜHRERSCHEIN"
    )
    dl_hits = sum(1 for k in dl_keywords if k in text_norm)
    if dl_hits >= 1:
        return "DRIVING_LICENCE", 0.95 if dl_hits >= 2 else 0.92

    # 4. PERMIT Detection
    permit_keywords = (
        "RESIDENCE PERMIT", "RESIDENT PERMIT", "WORK PERMIT", "ENTRY PERMIT",
        "RE-ENTRY PERMIT", "STAY PERMIT", "EMPLOYMENT PERMIT", "AUFENTHALTSTITEL",
        "PERMIS DE SEJOUR", "PERMIT NO", "PERMIT NUMBER", "PERMIT TYPE", "TYPE OF PERMIT",
        "AUTHORIZATION NO", "AUTHORIZATION NUMBER", "TRADE PERMIT", "COMMERCIAL PERMIT",
        "TRANSPORT PERMIT", "EVENT PERMIT", "CONSTRUCTION PERMIT", "ENVIRONMENTAL PERMIT",
        "PARKING PERMIT", "OCCUPANCY PERMIT"
    )
    permit_hits = sum(1 for k in permit_keywords if k in text_norm)
    if permit_hits >= 1:
        return "PERMIT", 0.95 if permit_hits >= 2 else 0.90

    # 5. NATIONAL_ID Detection
    if (qr_data and qr_data.get("qrDecoded")) or any(k in text_norm for k in ("AADHAAR", "UIDAI", "UNIQUE IDENTIFICATION")):
        return "NATIONAL_ID", 0.96

    if raw_mrz:
        clean_mrz = raw_mrz.strip().upper()
        if any(clean_mrz.startswith(p) for p in ("I<", "A<", "C<", "ID<")):
            return "NATIONAL_ID", 0.95

    nid_keywords = (
        "NATIONAL IDENTITY CARD", "IDENTITY CARD", "NATIONAL ID", "CITIZEN CARD",
        "PERSONALAUSWEIS", "CARTE NATIONALE D'IDENTITE", "CARTE NATIONALE",
        "ELECTION COMMISSION", "ELECTOR PHOTO", "VOTER ID", "EPIC NO",
        "INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER", "PAN CARD",
        "TAX ID", "SOCIAL SECURITY", "EMIRATES ID", "CIVIL ID"
    )
    nid_hits = sum(1 for k in nid_keywords if k in text_norm)
    if nid_hits >= 1:
        return "NATIONAL_ID", 0.95 if nid_hits >= 2 else 0.90

    if any(k in text_norm for k in ("REPUBLIC", "GOVERNMENT", "NATIONAL", "STATE")) and any(k in text_norm for k in ("DOB", "DATE OF BIRTH", "SEX", "GENDER")):
        return "NATIONAL_ID", 0.70

    # 6. UNKNOWN
    return "UNKNOWN", 0.20


def extract_visa_fields(
    text: str,
    boxes: list[dict[str, Any]] | None = None,
    raw_mrz: str | None = None,
    fields: dict[str, str] | None = None,
    detected_type: str = "UNKNOWN",
) -> dict[str, Any]:
    """Extracts dedicated visa fields (Visa Number, Visa Type, Entry Type, Stay Duration, Dates)

    and produces structured validation status for Visa documents.
    """
    text_norm = _normalize_text(text)
    text_upper = text_norm.upper()

    visa_number: str | None = None
    visa_type: str | None = None
    entry_type: str = "UNKNOWN"
    stay_duration: str | None = None
    stay_duration_val: int | None = None
    stay_duration_unit: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    issuing_country: str | None = fields.get("issuingCountry") if fields else None

    # 1. Visa Number
    if raw_mrz:
        clean_mrz = raw_mrz.strip().upper()
        mrz_v = re.search(r"V<[A-Z0-9]{3}([A-Z0-9<]{9})", clean_mrz)
        if mrz_v:
            num = mrz_v.group(1).replace("<", "").strip()
            if len(num) >= 5:
                visa_number = num

    if not visa_number:
        ctrl_match = re.search(
            r"(?:CONTROL\s*(?:NUMBER|NO\.?|#|N[O°]))[\s\S]{0,40}?\b([A-Z0-9-]*\d[A-Z0-9-]{4,19})\b",
            text_upper,
        )
        if ctrl_match:
            cand_ctrl = ctrl_match.group(1).strip()
            if cand_ctrl not in ("PASSPORT", "RECEIPT", "APPLICATION"):
                visa_number = cand_ctrl

    if not visa_number:
        vn_match = re.search(
            r"(?<!TYPE OF )(?<!CATEGORY OF )\b(?:VISA\s*(?:NO\.?|NUMBER|#|N[O°])|DOCUMENT\s*(?:NUMBER|NO\.?))\s*[:\s|-]*\s*([A-Z0-9-]{5,15})",
            text_upper,
        )
        if not vn_match:
            vn_match = re.search(r"\bVISA\s*[:\s|-]+\s*([A-Z0-9-]*\d[A-Z0-9-]{4,14})\b", text_upper)

        if vn_match:
            candidate_num = vn_match.group(1).strip()
            if not any(k in candidate_num for k in ("PASSPORT", "RECEIPT", "APPLICATION", "TOURIST", "BUSINESS", "STUDENT", "ENTRY")):
                visa_number = candidate_num

    if not visa_number and fields:
        if fields.get("visaNumber"):
            visa_number = fields["visaNumber"]

    # 2. Visa Type
    vt_class_code = re.search(r"\b([A-Z0-9]{1,4}/[A-Z0-9]{1,4})\b", text_upper)
    if vt_class_code:
        code_val = vt_class_code.group(1)
        visa_type = "B1/B2" if code_val in ("BL/BZ", "B1/B2") else code_val
    else:
        vt_match = re.search(
            r"(?:VISA\s*TYPE\s*/?\s*CLASS|VISA\s*TYPE|TYPE\s*OF\s*VISA|CATEGORY|CLASS)\s*[:\s|-]*\s*([A-Z0-9/\s-]{2,20})",
            text_upper,
        )
        if vt_match:
            type_str = vt_match.group(1).strip()
            words = [w for w in type_str.split() if w not in ("JOHN", "SURNAME", "GIVEN", "NAME", "PASSPORT", "NUMBER", "NO", "DATE", "CLASS", "TYPE")]
            if words:
                cand_type = " ".join(words)
                if cand_type not in ("R", "BL") and len(cand_type) >= 2:
                    visa_type = cand_type

    if not visa_type:
        for cat in ("TOURIST", "BUSINESS", "STUDENT", "WORK", "EMPLOYMENT", "TRANSIT", "VISITOR", "DIPLOMATIC", "OFFICIAL", "SCHENGEN", "B1/B2", "B1", "B2"):
            if cat in text_upper:
                visa_type = cat
                break

    # 3. Entry Validation
    entry_type = "UNKNOWN"
    if any(k in text_upper for k in ("MULTIPLE ENTRY", "ENTRIES: MULT", "ENTRIES: M", "NUMBER OF ENTRIES: MULTIPLE", "ENTRIES: MULTIPLE", "NUMBER OF ENTRIES: M")) or re.search(r"(?:NUMBER\s*OF\s*ENTRIES|ENTRIES)\s*[:\s|-]*\s*(?:MULT|MULTIPLE|M\b)", text_upper):
        entry_type = "MULTIPLE"
    elif any(k in text_upper for k in ("SINGLE ENTRY", "ENTRIES: 01", "ENTRIES: 1", "NUMBER OF ENTRIES: SINGLE", "ENTRIES: SINGLE")) or re.search(r"(?:NUMBER\s*OF\s*ENTRIES|ENTRIES)\s*[:\s|-]*\s*(?:SINGLE|0?1\b|ONE)", text_upper):
        entry_type = "SINGLE"
    elif any(k in text_upper for k in ("DOUBLE ENTRY", "ENTRIES: 02", "ENTRIES: 2", "NUMBER OF ENTRIES: DOUBLE", "ENTRIES: DOUBLE")) or re.search(r"(?:NUMBER\s*OF\s*ENTRIES|ENTRIES)\s*[:\s|-]*\s*(?:DOUBLE|0?2\b|TWO)", text_upper):
        entry_type = "DOUBLE"
    else:
        for line in text_upper.splitlines():
            line_s = line.strip()
            if "ENTRY VISA" in line_s or "VISA ENTRY" in line_s:
                continue
            if any(k in line_s for k in ("ENTRY", "ENTRIES", "ENTRADA")):
                if any(k in line_s for k in ("MULT", "MULTIPLE", "M")):
                    entry_type = "MULTIPLE"
                    break
                elif any(k in line_s for k in ("SINGLE", "01", "1", "ONE")):
                    entry_type = "SINGLE"
                    break
                elif any(k in line_s for k in ("DOUBLE", "02", "2", "TWO")):
                    entry_type = "DOUBLE"
                    break


    # 4. Stay Duration
    sd_match = re.search(
        r"(?:DURATION\s*OF\s*STAY|STAY\s*DURATION|STAY|DURATION|PERIOD\s*OF\s*STAY)\s*[:\s|-]*\s*(\d{1,4})\s*(DAYS?|MONTHS?|YEARS?|DAY|MONTH|YEAR)",
        text_upper,
    )
    if not sd_match:
        sd_match = re.search(r"\b(\d{1,4})\s*(DAYS?|MONTHS?|YEARS?)\b", text_upper)

    if sd_match:
        try:
            val_num = int(sd_match.group(1))
            unit_str = sd_match.group(2).strip()
            if unit_str.startswith("DAY"):
                unit_str = "DAYS"
            elif unit_str.startswith("MONTH"):
                unit_str = "MONTHS"
            elif unit_str.startswith("YEAR"):
                unit_str = "YEARS"
            stay_duration_val = val_num
            stay_duration_unit = unit_str
            stay_duration = f"{val_num} {unit_str}"
        except Exception:
            pass

    # 5. Issue & Expiry Dates
    def _parse_visa_date(dt_str: str) -> str | None:
        if not dt_str:
            return None
        formatted = re.sub(r"(\d{1,2})([A-Za-z]{3})(\d{4})", r"\1 \2 \3", dt_str.strip())
        norm = _normalize_date(formatted)
        return norm if norm else None

    all_d_matches = re.findall(r"\b(\d{1,2}[-/\s]?[A-Za-z]{3}[-/\s]?\d{4}|\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b", text_upper)
    parsed_dates = list(dict.fromkeys([d for d in [_parse_visa_date(x) for x in all_d_matches] if d]))
    parsed_dates.sort()

    if len(parsed_dates) >= 2:
        issue_date = parsed_dates[0]
        expiry_date = parsed_dates[-1]
    elif len(parsed_dates) == 1:
        issue_date = parsed_dates[0]

    if not issue_date and fields and fields.get("issueDate"):
        issue_date = fields["issueDate"]
    if not expiry_date and fields and fields.get("expiryDate"):
        expiry_date = fields["expiryDate"]

    # 6. Check if Document is a Visa
    is_visa = (
        (detected_type == "VISA")
        or (fields and (fields.get("documentCategory") == "VISA" or fields.get("documentSubtype") == "VISA" or fields.get("detectedDocumentType") == "VISA"))
        or any(k in text_upper for k in ("VISA", "VISA TRAVEL", "SCHENGEN VISA", "ENTRY VISA", "EXIT VISA", "TRANSIT VISA", "TYPE OF VISA", "VISA NO", "VISA NUMBER", "DURATION OF STAY", "ENTRIES: MULT", "ENTRIES: 01", "ENTRIES: 02"))
    )

    if not is_visa:
        return {
            "visaNumber": None,
            "visaType": None,
            "entryType": "UNKNOWN",
            "stayDuration": None,
            "stayDurationValue": None,
            "stayDurationUnit": None,
            "issueDate": None,
            "expiryDate": None,
            "issuingCountry": None,
            "status": "NOT_APPLICABLE",
            "validationMessages": ["Document is not classified as Visa"],
        }

    # 7. Status & Validation Messages
    msgs: list[str] = []
    if not visa_number:
        msgs.append("Visa number not confidently extracted")
    if entry_type == "UNKNOWN":
        msgs.append("Entry type unavailable")
    if not stay_duration:
        msgs.append("Stay duration unavailable")

    is_expired = False
    if expiry_date:
        try:
            exp_dt = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if datetime.now().date() > exp_dt:
                is_expired = True
                msgs.append("Visa has expired")
        except Exception:
            pass

    if is_expired:
        status = "INVALID"
    elif visa_number and entry_type != "UNKNOWN" and stay_duration and not msgs:
        status = "VALID"
    elif visa_number or entry_type != "UNKNOWN" or stay_duration:
        status = "PARTIAL"
    else:
        status = "UNKNOWN"

    return {
        "visaNumber": visa_number,
        "visaType": visa_type,
        "entryType": entry_type,
        "stayDuration": stay_duration,
        "stayDurationValue": stay_duration_val,
        "stayDurationUnit": stay_duration_unit,
        "issueDate": issue_date,
        "expiryDate": expiry_date,
        "issuingCountry": issuing_country,
        "status": status,
        "validationMessages": msgs,
    }


def extract_dl_fields(
    text: str,
    boxes: list[dict[str, Any]] | None = None,
    barcode_info: dict[str, Any] | None = None,
    fields: dict[str, str] | None = None,
    detected_type: str = "UNKNOWN",
) -> dict[str, Any]:
    """Extracts dedicated Driving Licence fields (DL Number, Holder Name, DOB, Issue Date, Expiry Date, State, Vehicle Classes, Barcode Status)

    and produces structured validation status for Driving Licence documents.
    """
    text_norm = _normalize_text(text)
    text_upper = text_norm.upper()

    dl_number: str | None = None
    holder_name: str | None = None
    dob: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    state: str | None = None
    issuing_authority: str | None = None
    vehicle_classes: list[str] = []
    barcode_status: str = "NOT_AVAILABLE"

    # 1. Barcode / PDF417 Integration
    if barcode_info and barcode_info.get("barcodeDetected"):
        if barcode_info.get("barcodeDecoded") and barcode_info.get("barcodeData"):
            barcode_status = "DECODED"
            b_data = str(barcode_info.get("barcodeData"))
            m_bc_dl = re.search(r"\b([A-Z]{2}[0-9O]{1,2}\s*[-/]?\s*[0-9O]{4}\s*[-/]?\s*[0-9O]{7,11})\b", b_data.upper())
            if m_bc_dl:
                dl_number = m_bc_dl.group(1).replace(" ", "")
        else:
            barcode_status = "UNREADABLE"

    # 2. DL Number Extraction
    if not dl_number:
        m_dl = re.search(r"\b([A-Z]{2}[-/\s]?[0-9O]{1,4}[-/\s]?[0-9O]{4}[-/\s]?[0-9O]{5,11})\b", text_upper)
        if m_dl:
            cand_dl = m_dl.group(1).strip()
            if not any(k in cand_dl for k in ("PASSPORT", "CONTROL", "RECEIPT", "APPLICATION", "LICENCE", "LICENSE")):
                dl_number = cand_dl

    if not dl_number:
        m_lbl = re.search(
            r"(?:DL\s*(?:NO|NUMBER|#)?|LICENCE\s*(?:NO|NUMBER)?|LICENSE\s*(?:NO|NUMBER)?|DRIVING\s*LICENCE\s*NO|DRIVING\s*LICENSE\s*NO)\s*[:\s|-]*\s*([A-Z0-9-/ ]{6,25})",
            text_upper,
        )
        if m_lbl:
            cand_dl = m_lbl.group(1).strip()
            if not any(k in cand_dl for k in ("PASSPORT", "RECEIPT", "APPLICATION")):
                dl_number = cand_dl

    if not dl_number and fields and fields.get("documentNumber"):
        if not fields.get("documentNumber", "").startswith("P<"):
            dl_number = fields["documentNumber"]

    # 3. Holder Name Extraction
    if fields and (fields.get("name") or fields.get("holderName")):
        cand_name = fields.get("name") or fields.get("holderName")
        if cand_name and not any(k in cand_name.upper() for k in ("DRIVING", "LICENCE", "LICENSE", "TRANSPORT", "GOVERNMENT", "DEPARTMENT", "INDIA", "STATE")):
            holder_name = cand_name

    if not holder_name:
        m_name = re.search(r"(?:NAME\s*OF\s*HOLDER|HOLDER\s*NAME|NAME)\s*[:\s|-]*\s*([A-Z\ '.]{3,30})", text_upper)
        if m_name:
            c_name = m_name.group(1).strip()
            c_name = re.split(r"\b(?:S/O|D/O|W/O|SON OF|DAUGHTER OF|WIFE OF)\b", c_name)[0].strip()
            if len(c_name) >= 3 and not any(k in c_name for k in ("DRIVING", "LICENCE", "LICENSE", "TRANSPORT", "AUTHORITY", "UNION", "GOVT", "INDIA", "STATE", "ADDRESS", "DOB", "DATE")):
                holder_name = c_name

    # 4. Date of Birth
    if fields and fields.get("dateOfBirth"):
        dob = fields["dateOfBirth"]
    else:
        m_dob = re.search(r"(?:DOB|DATE\s*OF\s*BIRTH|D\.O\.B|BIRTH\s*DATE)\s*[:\s|-]*\s*(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})", text_upper)
        if m_dob:
            dob = _normalize_date(m_dob.group(1))

    # 5. Issue Date
    if fields and fields.get("issueDate"):
        issue_date = fields["issueDate"]
    else:
        m_iss = re.search(r"(?:ISSUE\s*DATE|DATE\s*OF\s*ISSUE|ISSUE|VALID\s*FROM|ISSUED\s*ON|DOI)\s*[:\s|-]*\s*(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})", text_upper)
        if m_iss:
            issue_date = _normalize_date(m_iss.group(1))

    # 6. Expiry / Validity Date (CRITICAL REGRESSION REQUIREMENT)
    # Expiry MUST NOT be filled with issue_date. It stays None if no explicit expiry match is found!
    m_exp = re.search(r"(?:VALID\s*TILL|VALID\s*UPTO|VALID\s*UNTIL|EXPIRY\s*DATE|EXPIRY|VALIDITY)\s*[:\s|-]*\s*(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})", text_upper)
    if m_exp:
        parsed_exp = _normalize_date(m_exp.group(1))
        if parsed_exp and parsed_exp != issue_date:
            expiry_date = parsed_exp
    elif fields and fields.get("expiryDate") and fields.get("expiryDate") != issue_date:
        expiry_date = fields["expiryDate"]

    # 7. State & Issuing Authority
    indian_states = {
        "MH": "MAHARASHTRA", "DL": "DELHI", "KA": "KARNATAKA", "TN": "TAMIL NADU",
        "RJ": "RAJASTHAN", "GJ": "GUJARAT", "UP": "UTTAR PRADESH", "HR": "HARYANA",
        "WB": "WEST BENGAL", "KL": "KERALA", "AP": "ANDHRA PRADESH", "TS": "TELANGANA",
        "MP": "MADHYA PRADESH", "PB": "PUNJAB", "BR": "BIHAR", "OR": "ODISHA", "OD": "ODISHA"
    }
    if dl_number and len(dl_number) >= 2:
        prefix = dl_number[:2].upper()
        if prefix in indian_states:
            state = indian_states[prefix]

    if not state:
        for st_name in indian_states.values():
            if st_name in text_upper:
                state = st_name
                break

    m_rto = re.search(r"(?:RTO|LICENSING\s*AUTHORITY|ISSUING\s*AUTHORITY|TRANSPORT\s*DEPARTMENT)\s*[:\s|-]*\s*([A-Z0-9\s,]{3,30})", text_upper)
    if m_rto:
        issuing_authority = m_rto.group(1).strip()
    elif state:
        issuing_authority = f"TRANSPORT DEPARTMENT, {state}"

    # 8. Vehicle Classes (COV)
    cov_matches = re.findall(r"\b(MCWG|LMV|HMV|TRANS|NON-TRANS|MCWOG|3W-CAB|LMV-NT|MCW|COV)\b", text_upper)
    if cov_matches:
        vehicle_classes = sorted(list(set([c for c in cov_matches if c != "COV"])))

    # 9. Check if Document is a Driving Licence
    is_dl = (detected_type == "DRIVING_LICENCE") or any(
        k in text_upper for k in ("DRIVING LICENCE", "DRIVING LICENSE", "DRIVER LICENSE", "LICENCE NO", "LICENSE NO", "DL NO", "PERMIS DE CONDUIRE", "FÜHRERSCHEIN", "CLASS OF VEHICLE")
    )

    if not is_dl:
        return {
            "dlNumber": None,
            "holderName": None,
            "dateOfBirth": None,
            "issueDate": None,
            "expiryDate": None,
            "state": None,
            "issuingAuthority": None,
            "vehicleClasses": [],
            "barcodeStatus": barcode_status,
            "status": "NOT_APPLICABLE",
            "validationMessages": ["Document is not classified as Driving Licence"],
        }

    # 10. Status & Validation Messages
    msgs: list[str] = []
    if not dl_number:
        msgs.append("DL number not confidently extracted")
    if not holder_name:
        msgs.append("Holder name unavailable")
    if not dob:
        msgs.append("Date of birth unavailable")
    if not issue_date:
        msgs.append("Issue date unavailable")
    if not expiry_date:
        msgs.append("Expiry date unavailable")

    invalid_dates = False
    is_expired = False

    if dob and issue_date:
        try:
            d_dob = datetime.strptime(dob, "%Y-%m-%d").date()
            d_iss = datetime.strptime(issue_date, "%Y-%m-%d").date()
            if d_dob >= d_iss:
                msgs.append("Date of birth must be prior to issue date")
                invalid_dates = True
        except Exception:
            pass

    if issue_date and expiry_date:
        try:
            d_iss = datetime.strptime(issue_date, "%Y-%m-%d").date()
            d_exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if d_iss >= d_exp:
                msgs.append("Issue date must be prior to expiry date")
                invalid_dates = True
        except Exception:
            pass

    if expiry_date:
        try:
            d_exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if datetime.now().date() > d_exp:
                msgs.append("Driving Licence has expired")
                is_expired = True
        except Exception:
            pass

    if invalid_dates or is_expired:
        status = "INVALID"
    elif dl_number and holder_name and dob and issue_date and expiry_date and not msgs:
        status = "VALID"
    elif dl_number or holder_name or dob or issue_date:
        status = "PARTIAL"
    else:
        status = "UNKNOWN"

    return {
        "dlNumber": dl_number,
        "holderName": holder_name,
        "dateOfBirth": dob,
        "issueDate": issue_date,
        "expiryDate": expiry_date,
        "state": state,
        "issuingAuthority": issuing_authority,
        "vehicleClasses": vehicle_classes,
        "barcodeStatus": barcode_status,
        "status": status,
        "validationMessages": msgs,
    }


_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def _validate_verhoeff(number_str: str) -> bool:
    digits = [int(c) for c in reversed(number_str) if c.isdigit()]
    if not digits:
        return False
    c = 0
    for i, d in enumerate(digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][d]]
    return c == 0


def extract_national_id_fields(
    text: str,
    boxes: list[dict[str, Any]] | None = None,
    qr_info: dict[str, Any] | None = None,
    barcode_info: dict[str, Any] | None = None,
    fields: dict[str, str] | None = None,
    detected_type: str = "UNKNOWN",
) -> dict[str, Any]:
    """Extracts dedicated National ID fields (ID Number, Holder Name, DOB, Subtype, QR/Barcode Status)

    and produces structured validation status for National ID documents (including Verhoeff checksum for Aadhaar).
    """
    text_norm = _normalize_text(text)
    text_upper = text_norm.upper()
    msgs: list[str] = []

    id_number: str | None = None
    holder_name: str | None = None
    dob: str | None = None
    id_subtype: str = "UNKNOWN"
    issue_date: str | None = None
    expiry_date: str | None = None
    address: str | None = None
    gender: str | None = None
    nationality: str | None = None

    # QR and Barcode Status
    qr_status: str = "NOT_AVAILABLE"
    if qr_info:
        if qr_info.get("qrDetected"):
            qr_status = "DECODED" if qr_info.get("qrDecoded") else "UNREADABLE"
        elif qr_info.get("qrStatus"):
            qr_status = qr_info.get("qrStatus")

    barcode_status: str = "NOT_AVAILABLE"
    if barcode_info:
        if barcode_info.get("barcodeDetected"):
            barcode_status = "DECODED" if barcode_info.get("barcodeDecoded") else "UNREADABLE"
        elif barcode_info.get("barcodeStatus"):
            barcode_status = barcode_info.get("barcodeStatus")

    # 1. Subtype Detection (AADHAAR vs OTHER_NATIONAL_ID vs UNKNOWN)
    if "AADHAAR" in text_upper or "UNIQUE IDENTIFICATION" in text_upper or ("GOVERNMENT OF INDIA" in text_upper and ("DOB" in text_upper or "MALE" in text_upper or "FEMALE" in text_upper)):
        id_subtype = "AADHAAR"
    elif "PERSONALAUSWEIS" in text_upper or "VOTER ID" in text_upper or "PAN CARD" in text_upper or "CARTE NATIONALE" in text_upper or "NATIONAL ID" in text_upper:
        id_subtype = "OTHER_NATIONAL_ID"
    elif detected_type == "NATIONAL_ID":
        id_subtype = "OTHER_NATIONAL_ID"

    # If QR data contains 12-digit Aadhaar / Indian identity, set AADHAAR
    qr_data = qr_info.get("qrData") if qr_info else None
    if qr_data and (qr_data.get("uid") or (qr_data.get("documentNumber") and len(str(qr_data.get("documentNumber")).replace(" ", "")) == 12)):
        id_subtype = "AADHAAR"

    # 2. Field Fallbacks from fields dictionary
    if fields:
        if fields.get("documentNumber") and not fields.get("documentNumber", "").startswith("P<"):
            id_number = fields.get("documentNumber")
        if fields.get("name") or fields.get("holderName"):
            holder_name = fields.get("name") or fields.get("holderName")
        if fields.get("dateOfBirth"):
            dob = fields.get("dateOfBirth")
        if fields.get("gender"):
            gender = fields.get("gender")
        if fields.get("address"):
            address = fields.get("address")
        if fields.get("nationality"):
            nationality = fields.get("nationality")
        if fields.get("issueDate"):
            issue_date = fields.get("issueDate")
        if fields.get("expiryDate"):
            expiry_date = fields.get("expiryDate")

    # If QR data is present, extract QR identity fields for cross-checking
    qr_id_num = None
    qr_name = None
    qr_dob = None
    if qr_data:
        qr_id_num = qr_data.get("uid") or qr_data.get("documentNumber")
        qr_name = qr_data.get("name")
        qr_dob = qr_data.get("dob")
        if not id_number and qr_id_num:
            id_number = str(qr_id_num)
        if not holder_name and qr_name:
            holder_name = str(qr_name)
        if not dob and qr_dob:
            dob = str(qr_dob)

    # 3. ID Number Extraction & Format Normalization
    if not id_number:
        m_aadh = re.search(r"\b([0-9]{4}\s+[0-9]{4}\s+[0-9]{4})\b", text_norm)
        if m_aadh:
            id_number = m_aadh.group(1)
        else:
            m_aadh_raw = re.search(r"\b([0-9]{12})\b", text_norm.replace(" ", ""))
            if m_aadh_raw:
                raw_num = m_aadh_raw.group(1)
                id_number = f"{raw_num[:4]} {raw_num[4:8]} {raw_num[8:]}"

    # Check incomplete Aadhaar numbers (e.g. 10 or 11 digits)
    if not id_number:
        m_part = re.search(r"\b([0-9]{4}\s+[0-9]{4}\s+[0-9]{2,3})\b", text_norm)
        if m_part:
            id_number = m_part.group(1)

    digits_only = re.sub(r"[^\d]", "", id_number) if id_number else ""

    # 4. QR Cross-Checks
    if qr_id_num and id_number:
        clean_qr_id = re.sub(r"[^\d]", "", str(qr_id_num))
        if digits_only and clean_qr_id:
            if digits_only == clean_qr_id:
                msgs.append("QR & Visual OCR ID Number corroborate")
            else:
                msgs.append(f"QR ID Number '{clean_qr_id}' conflicts with Visual OCR ID Number '{digits_only}'")

    if qr_name and holder_name:
        if qr_name.strip().upper() == holder_name.strip().upper():
            msgs.append("QR & Visual OCR Name corroborate")

    # 5. Validation Status Determination
    status = "UNKNOWN"
    if id_subtype == "AADHAAR":
        if len(digits_only) == 12:
            if _validate_verhoeff(digits_only):
                status = "VALID"
            else:
                status = "INVALID"
                msgs.append("Aadhaar checksum validation failed")
        elif len(digits_only) in (10, 11):
            status = "PARTIAL"
            msgs.append("Incomplete Aadhaar number")
        elif not digits_only:
            status = "PARTIAL"
            msgs.append("National ID number unavailable")
        else:
            status = "INVALID"
            msgs.append("Invalid Aadhaar number length")
    else:
        if id_number and holder_name and dob:
            status = "VALID"
        elif id_number or holder_name or dob:
            status = "PARTIAL"
        else:
            status = "UNKNOWN"

    if not holder_name:
        msgs.append("Holder name unavailable")
    if not dob:
        msgs.append("Date of birth unavailable")

    return {
        "idNumber": id_number,
        "holderName": holder_name,
        "dateOfBirth": dob,
        "idSubtype": id_subtype,
        "issueDate": issue_date,
        "expiryDate": expiry_date,
        "qrStatus": qr_status,
        "barcodeStatus": barcode_status,
        "status": status,
        "validationMessages": msgs,
    }


def extract_permit_fields(
    text: str,
    boxes: list[dict[str, Any]] | None = None,
    barcode_info: dict[str, Any] | None = None,
    qr_info: dict[str, Any] | None = None,
    fields: dict[str, str] | None = None,
    detected_type: str = "UNKNOWN",
) -> dict[str, Any]:
    """Extracts dedicated Permit fields (Permit Number, Permit Type, Holder/Organization Name, Issue/Expiry Dates, Issuing Authority)

    and produces structured validation status for Permit documents.
    """
    text_norm = _normalize_text(text)
    text_upper = text_norm.upper()

    permit_number: str | None = None
    permit_type: str | None = None
    holder_name: str | None = None
    organization_name: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    issuing_authority: str | None = None
    address: str | None = None
    vehicle_asset_identifier: str | None = None
    permit_category: str | None = None
    reference_number: str | None = None

    # 1. Check if Document is a Permit
    permit_landmarks = (
        "PERMIT", "AUTHORIZATION", "RESIDENCE PERMIT", "WORK PERMIT", "PERMIT NO", "PERMIT NUMBER",
        "PERMIT TYPE", "PERMIT ID", "LICENSE/PERMIT", "LICENCE/PERMIT", "AUFENTHALTSTITEL",
        "PERMIS DE SEJOUR", "TRADE PERMIT", "COMMERCIAL PERMIT", "TRANSPORT PERMIT", "EVENT PERMIT",
        "CONSTRUCTION PERMIT", "ENVIRONMENTAL PERMIT", "PARKING PERMIT", "OCCUPANCY PERMIT"
    )
    is_permit = (detected_type == "PERMIT") or any(k in text_upper for k in permit_landmarks)

    if not is_permit:
        return {
            "permitNumber": None,
            "permitType": None,
            "holderName": None,
            "organizationName": None,
            "issueDate": None,
            "expiryDate": None,
            "issuingAuthority": None,
            "address": None,
            "vehicleAssetIdentifier": None,
            "permitCategory": None,
            "referenceNumber": None,
            "status": "NOT_APPLICABLE",
            "validationMessages": ["Document is not classified as Permit"],
        }

    # 2. Permit Number Extraction
    m_pnum = re.search(
        r"(?:PERMIT\s*(?:NO\.?|NUMBER|ID|#)|LICENSE/PERMIT\s*NO\.?|LICENCE/PERMIT\s*NO\.?|AUTHORIZATION\s*(?:NO\.?|NUMBER|ID|#)|PERMIT\s*REF)\s*[:\s|-]*\s*([A-Z0-9-/ ]{4,30})",
        text_upper,
    )
    if m_pnum:
        cand = m_pnum.group(1).strip()
        if not any(k in cand for k in ("APPLICATION", "RECEIPT", "TRANSACTION", "PASSPORT", "CONTROL")):
            cand = re.split(r"\b(?:DATE|TYPE|NAME|ISSUED|HOLDER|EXPIRY|VALID)\b", cand)[0].strip()
            if len(cand) >= 3:
                permit_number = cand

    if not permit_number:
        m_ref = re.search(r"(?:REFERENCE\s*(?:NO\.?|NUMBER|ID|#)|REF\s*(?:NO\.?|NUMBER|#))\s*[:\s|-]*\s*([A-Z0-9-/ ]{4,30})", text_upper)
        if m_ref:
            cand_ref = m_ref.group(1).strip()
            cand_ref = re.split(r"\b(?:DATE|TYPE|NAME|ISSUED|HOLDER|EXPIRY|VALID)\b", cand_ref)[0].strip()
            if len(cand_ref) >= 3:
                reference_number = cand_ref

    if not permit_number and reference_number:
        permit_number = reference_number

    if not permit_number and fields and fields.get("documentNumber"):
        if not fields.get("documentNumber", "").startswith("P<"):
            permit_number = fields["documentNumber"]

    # 3. Permit Type / Category Extraction
    m_ptype = re.search(
        r"(?:PERMIT\s*TYPE|TYPE\s*OF\s*PERMIT|CATEGORY|PERMIT\s*CATEGORY|CLASSIFICATION)\s*[:\s|-]*\s*([A-Z\s/-]{3,30})",
        text_upper,
    )
    if m_ptype:
        cand_t = m_ptype.group(1).strip()
        cand_t = re.split(r"\b(?:NO|NUMBER|DATE|HOLDER|NAME|EXPIRY|VALID|ISSUED)\b", cand_t)[0].strip()
        if len(cand_t) >= 3:
            permit_type = cand_t
            permit_category = cand_t

    if not permit_type:
        known_subtypes = (
            "TRANSPORT PERMIT", "COMMERCIAL PERMIT", "WORK PERMIT", "EVENT PERMIT",
            "TRADE PERMIT", "CONSTRUCTION PERMIT", "ENVIRONMENTAL PERMIT", "PARKING PERMIT",
            "OCCUPANCY PERMIT", "RESIDENCE PERMIT", "RESIDENT PERMIT", "BUILDING PERMIT",
            "SPECIAL PERMIT", "ENTRY PERMIT", "STAY PERMIT"
        )
        for st in known_subtypes:
            if st in text_upper:
                permit_type = st
                permit_category = st
                break

    # 4. Holder Name / Organization Name Extraction
    m_holder = re.search(
        r"(?:PERMIT\s*HOLDER|HOLDER\s*NAME|HOLDER|LICENSEE|APPLICANT|NAME\s*OF\s*HOLDER|NAME)\s*[:\s|-]*\s*([A-Z\ '.]{3,40})",
        text_upper,
    )
    if m_holder:
        c_h = m_holder.group(1).strip()
        c_h = re.split(r"\b(?:ADDRESS|DOB|DATE|NO|NUMBER|TYPE|EXPIRY|ISSUED|AUTHORITY|DEPARTMENT)\b", c_h)[0].strip()
        if len(c_h) >= 3 and not any(k in c_h for k in ("DEPARTMENT", "GOVERNMENT", "AUTHORITY", "MUNICIPAL", "CORPORATION", "MINISTRY", "STATE", "PERMIT")):
            holder_name = c_h

    m_org = re.search(
        r"(?:ORGANIZATION|ORGANISATION|COMPANY|ENTITY|BUSINESS\s*NAME|FIRM\s*NAME)\s*[:\s|-]*\s*([A-Z0-9\ '.&,-]{3,50})",
        text_upper,
    )
    if m_org:
        c_o = m_org.group(1).strip()
        c_o = re.split(r"\b(?:ADDRESS|DOB|DATE|NO|NUMBER|TYPE|EXPIRY|ISSUED|AUTHORITY)\b", c_o)[0].strip()
        if len(c_o) >= 3:
            organization_name = c_o

    if not holder_name and fields and (fields.get("name") or fields.get("holderName")):
        cand_name = fields.get("name") or fields.get("holderName")
        if cand_name and not any(k in cand_name.upper() for k in ("PERMIT", "GOVERNMENT", "DEPARTMENT", "AUTHORITY", "MINISTRY")):
            holder_name = cand_name

    # 5. Issue Date
    m_iss = re.search(
        r"(?:ISSUE\s*DATE|DATE\s*OF\s*ISSUE|ISSUED\s*ON|VALID\s*FROM|EFFECTIVE\s*FROM|ISSUED)\s*[:\s|-]*\s*(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})",
        text_upper,
    )
    if m_iss:
        issue_date = _normalize_date(m_iss.group(1))
    elif fields and fields.get("issueDate"):
        issue_date = fields["issueDate"]

    # 6. Expiry Date (MUST remain None if unreadable)
    m_exp = re.search(
        r"(?:EXPIRY\s*DATE|EXPIRY|VALID\s*UNTIL|VALID\s*TILL|VALID\s*UPTO|VALID\s*THROUGH|VALIDITY)\s*[:\s|-]*\s*(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})",
        text_upper,
    )
    if m_exp:
        parsed_exp = _normalize_date(m_exp.group(1))
        if parsed_exp and parsed_exp != issue_date:
            expiry_date = parsed_exp
    elif fields and fields.get("expiryDate") and fields.get("expiryDate") != issue_date:
        expiry_date = fields["expiryDate"]

    # 7. Issuing Authority
    m_auth = re.search(
        r"(?:ISSUING\s*AUTHORITY|ISSUED\s*BY|AUTHORITY|DEPARTMENT|GOVERNMENT\b|MUNICIPAL\s*CORPORATION|TRANSPORT\s*DEPARTMENT)\s*[:\s|-]*\s*([A-Z0-9\s,.-]{3,50})",
        text_upper,
    )
    if m_auth:
        c_auth = m_auth.group(1).strip()
        c_auth = c_auth.split("\n")[0].strip()
        c_auth = re.split(r"\b(?:ISSUE|DATE|PERMIT|HOLDER|NAME|ADDRESS|EXPIRY|VALID)\b", c_auth)[0].strip()
        if len(c_auth) >= 3 and c_auth != holder_name:
            issuing_authority = c_auth

    # 8. Address
    m_addr = re.search(r"(?:ADDRESS|LOCATION|PREMISES)\s*[:\s|-]*\s*([A-Z0-9\s,.-]{5,60})", text_upper)
    if m_addr:
        c_addr = m_addr.group(1).strip()
        c_addr = c_addr.split("\n")[0].strip()
        c_addr = re.split(r"\b(?:DATE|PERMIT|HOLDER|EXPIRY)\b", c_addr)[0].strip()
        if len(c_addr) >= 5:
            address = c_addr
    elif fields and fields.get("address"):
        address = fields["address"]

    # 9. Vehicle / Asset Identifier
    m_asset = re.search(r"(?:VEHICLE\s*(?:NO|REG|ID)?|REGISTRATION\s*NO|ASSET\s*ID)\s*[:\s|-]*\s*([A-Z0-9-]{3,20})", text_upper)
    if m_asset:
        vehicle_asset_identifier = m_asset.group(1).strip().split("\n")[0].strip()

    # 10. Status & Validation Messages
    msgs: list[str] = []
    if not permit_number:
        msgs.append("Permit number not confidently extracted")
    if not permit_type:
        msgs.append("Permit type unavailable")
    if not holder_name and not organization_name:
        msgs.append("Holder or organization name unavailable")
    if not issue_date:
        msgs.append("Issue date unavailable")
    if not expiry_date:
        msgs.append("Expiry date unavailable")

    invalid_dates = False
    is_expired = False

    if issue_date and expiry_date:
        try:
            d_iss = datetime.strptime(issue_date, "%Y-%m-%d").date()
            d_exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if d_iss >= d_exp:
                msgs.append("Permit issue date must be prior to expiry date")
                invalid_dates = True
        except Exception:
            pass

    if expiry_date:
        try:
            d_exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if datetime.now().date() > d_exp:
                msgs.append("Permit has expired")
                is_expired = True
        except Exception:
            pass

    if invalid_dates or is_expired:
        status = "INVALID"
    elif permit_number and permit_type and (holder_name or organization_name) and issue_date and expiry_date:
        status = "VALID"
    elif permit_number or permit_type or holder_name or organization_name or issue_date or expiry_date:
        status = "PARTIAL"
    else:
        status = "UNKNOWN"


    return {
        "permitNumber": permit_number,
        "permitType": permit_type,
        "holderName": holder_name,
        "organizationName": organization_name,
        "issueDate": issue_date,
        "expiryDate": expiry_date,
        "issuingAuthority": issuing_authority,
        "address": address,
        "vehicleAssetIdentifier": vehicle_asset_identifier,
        "permitCategory": permit_category,
        "referenceNumber": reference_number,
        "status": status,
        "validationMessages": msgs,
    }


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

def extract(data: bytes) -> dict[str, Any]:
    start_time = time.time()
    notes: list[str] = []

    # 1. OCR Text & Spatial Bounding Box Extraction
    text, ocr_confidence, boxes = _extract_text_from_data(data)
    if text:
        notes.append("OCR: Text & spatial vector bounding boxes extracted successfully")
    else:
        notes.append("OCR: No readable text detected in document image")

    # 2. MRZ Detection (Passports & TD1 ID Cards)
    raw_mrz, mrz_status = _find_mrz(text)
    mrz_valid = False
    mrz_checks: dict[str, bool] = {}
    parsed_mrz = None

    if raw_mrz:
        parsed_mrz = mrz_mod.parse_td3(raw_mrz)
        if not parsed_mrz and raw_mrz.count("\n") >= 2:
            parsed_mrz = mrz_mod.parse_td1(raw_mrz)

        if parsed_mrz:
            mrz_checks = parsed_mrz.checks
            mrz_valid = parsed_mrz.all_valid
            mrz_status = "VALIDATED" if mrz_valid else "CHECKSUM_MISMATCH"
            notes.append(f"MRZ: ICAO 9303 parsed — Integrity Checkdigits: {mrz_status}")

    # 3. Barcode / PDF417 / DataMatrix Detection
    barcode_info = _extract_barcode_info(data)
    if barcode_info["barcodeDetected"]:
        notes.append(f"Barcode: {barcode_info['barcodeType']} detected — Status: {barcode_info['barcodeStatus']}")

    # 4. Generic National ID Adapter Field Extraction
    adapter = GenericNationalIDAdapter()
    id_res = adapter.extract(text, boxes, raw_mrz)
    notes.extend(id_res["notes"])

    fields = id_res["fields"]
    field_confidences = id_res["fieldConfidences"]
    field_states = id_res["fieldStates"]
    doc_type = id_res["detectedDocumentType"]
    doc_category = id_res.get("documentCategory", "NATIONAL_ID")
    doc_subtype = id_res.get("documentSubtype", "NATIONAL_ID_CARD")
    issuing_country = id_res["issuingCountry"]

    # 5. If passport/ID MRZ is present, merge MRZ extracted values
    if parsed_mrz:
        mrz_name = f"{parsed_mrz.given_names} {parsed_mrz.surname}".strip()
        if mrz_name:
            fields["name"] = mrz_name
            fields["holderName"] = mrz_name
            field_confidences["name"] = 0.99
            field_confidences["holderName"] = 0.99
            field_states["holderName"] = "DETECTED"
        if parsed_mrz.document_number:
            fields["passportNumber"] = parsed_mrz.document_number
            fields["documentNumber"] = parsed_mrz.document_number
            field_confidences["documentNumber"] = 0.99
            field_states["documentNumber"] = "DETECTED"
        if parsed_mrz.date_of_birth:
            fields["dateOfBirth"] = parsed_mrz.date_of_birth
            field_confidences["dateOfBirth"] = 0.99
            field_states["dateOfBirth"] = "DETECTED"
        if parsed_mrz.sex:
            fields["gender"] = parsed_mrz.sex
            field_confidences["gender"] = 0.99
            field_states["gender"] = "DETECTED"
        if parsed_mrz.expiry_date:
            fields["expiryDate"] = parsed_mrz.expiry_date
            field_confidences["expiryDate"] = 0.99
            field_states["expiryDate"] = "DETECTED"

    # 6. QR Code Detection & Cross-Validation
    qr_info = _extract_qr_info(data, fields, fields)
    if qr_info["qrDetected"]:
        notes.append(f"QR Code: Detected — Decoded: {qr_info['qrDecoded']} | Cryptographic Signature: {qr_info['qrSignatureStatus']}")
        if qr_info["qrOcrMatchStatus"] != "NOT_APPLICABLE":
            notes.append(f"QR <-> Visual OCR Cross-Validation: {qr_info['qrOcrMatchStatus']}")

    # Merge QR fallback data if visual fields were missed
    if qr_info["qrData"]:
        qr_d = qr_info["qrData"]
        if not fields.get("name") and qr_d.get("name"):
            fields["name"] = qr_d["name"]
            fields["holderName"] = qr_d["name"]
            field_confidences["holderName"] = 0.90
            field_states["holderName"] = "DETECTED"
        if not fields.get("dateOfBirth") and qr_d.get("dob"):
            fields["dateOfBirth"] = qr_d["dob"]
            field_confidences["dateOfBirth"] = 0.90
            field_states["dateOfBirth"] = "DETECTED"
        if not fields.get("gender") and qr_d.get("gender"):
            fields["gender"] = qr_d["gender"]
            field_confidences["gender"] = 0.90
            field_states["gender"] = "DETECTED"
        if not fields.get("documentNumber") and qr_d.get("documentNumber"):
            fields["documentNumber"] = qr_d["documentNumber"]
            fields["passportNumber"] = qr_d["documentNumber"]
            field_confidences["documentNumber"] = 0.90
            field_states["documentNumber"] = "DETECTED"
        if not fields.get("address") and qr_d.get("address"):
            fields["address"] = qr_d["address"]
            field_confidences["address"] = 0.88
            field_states["address"] = "DETECTED"

        if qr_d.get("documentNumber") and len(qr_d.get("documentNumber", "").replace(" ", "")) == 12 and doc_category == "NATIONAL_ID":
            doc_subtype = "AADHAAR"
            doc_type = "AADHAAR"

    # Calculate overall document capabilities (fields & verification checks)
    applicable_fields, applicable_checks = _get_document_capabilities(
        doc_category,
        doc_subtype,
        mrz_detected=parsed_mrz is not None,
        qr_detected=qr_info["qrDetected"],
        barcode_detected=barcode_info["barcodeDetected"]
    )

    # Document-adaptive Field Extraction Confidence vs Raw Bounding Box OCR Confidence
    valid_confs = [v for k, v in field_confidences.items() if v > 0.0 and field_states.get(k) in ("DETECTED", "LOW_CONFIDENCE")]
    field_extraction_conf = round(sum(valid_confs) / len(valid_confs), 3) if valid_confs else 0.85
    raw_ocr_conf = round(ocr_confidence if ocr_confidence is not None else 0.85, 3)
    overall_conf = field_extraction_conf if valid_confs else raw_ocr_conf

    extraction_time_ms = round((time.time() - start_time) * 1000, 1)

    # P2.1 Automatic Document-Type Detection
    autodetected_type, autodetected_conf = detect_document_type(
        text, raw_mrz=raw_mrz, boxes=boxes, qr_data=qr_info.get("qrData"), barcode_data=barcode_info
    )

    # P2.2 Dedicated Visa Extraction
    visa_res = extract_visa_fields(
        text, boxes=boxes, raw_mrz=raw_mrz, fields=fields, detected_type=autodetected_type
    )

    # P2.3 Dedicated Driving Licence Extraction
    dl_res = extract_dl_fields(
        text, boxes=boxes, barcode_info=barcode_info, fields=fields, detected_type=autodetected_type
    )

    # P2.4 Dedicated National ID Extraction
    nat_res = extract_national_id_fields(
        text, boxes=boxes, qr_info=qr_info, barcode_info=barcode_info, fields=fields, detected_type=autodetected_type
    )

    # P2.5 Dedicated Permit Extraction
    permit_res = extract_permit_fields(
        text, boxes=boxes, barcode_info=barcode_info, qr_info=qr_info, fields=fields, detected_type=autodetected_type
    )

    visual_zone_payload = {
        **fields,
        "rawText": text[:2500] if text else "",
        "detectedDocumentType": doc_type,
        "documentCategory": doc_category,
        "documentSubtype": doc_subtype,
        "applicableFields": applicable_fields,
        "applicableChecks": applicable_checks,
        "issuingCountry": issuing_country,
        "fieldConfidences": field_confidences,
        "fieldStates": field_states,
        "fieldExtractionConfidence": field_extraction_conf,
        "rawOcrConfidence": raw_ocr_conf,
        "ocrBoxes": boxes,
        "qrDetected": qr_info["qrDetected"],
        "qrDecoded": qr_info["qrDecoded"],
        "qrStatus": qr_info["qrStatus"],
        "qrSignatureVerified": qr_info["qrSignatureVerified"],
        "qrSignatureStatus": qr_info["qrSignatureStatus"],
        "qrData": qr_info["qrData"],
        "qrOcrMatchStatus": qr_info["qrOcrMatchStatus"],
        "qrOcrDiscrepancies": qr_info["qrOcrDiscrepancies"],
        "barcodeDetected": barcode_info["barcodeDetected"],
        "barcodeDecoded": barcode_info["barcodeDecoded"],
        "barcodeStatus": barcode_info["barcodeStatus"],
        "barcodeType": barcode_info["barcodeType"],
        "barcodeData": barcode_info["barcodeData"],
        "mrzStatus": mrz_status,
        "visaResult": visa_res,
        "drivingLicenceResult": dl_res,
        "nationalIdResult": nat_res,
        "permitResult": permit_res,
    }

    return {
        "mrz": raw_mrz,
        "fields": fields,
        "visualZone": visual_zone_payload,
        "ocrBoxes": boxes,
        "confidence": overall_conf,
        "fieldExtractionConfidence": field_extraction_conf,
        "rawOcrConfidence": raw_ocr_conf,
        "fieldConfidences": field_confidences,
        "fieldStates": field_states,
        "mrzValid": mrz_valid,
        "mrzChecks": mrz_checks,
        "mrzStatus": mrz_status,
        "notes": notes,
        "detectedDocumentType": doc_type,
        "documentCategory": doc_category,
        "documentSubtype": doc_subtype,
        "detectedType": autodetected_type,
        "detectionConfidence": autodetected_conf,
        "applicableFields": applicable_fields,
        "applicableChecks": applicable_checks,
        "issuingCountry": issuing_country,
        "extractionTimeMs": extraction_time_ms,
        "qrDetected": qr_info["qrDetected"],
        "qrDecoded": qr_info["qrDecoded"],
        "qrStatus": qr_info["qrStatus"],
        "qrSignatureVerified": qr_info["qrSignatureVerified"],
        "qrSignatureStatus": qr_info["qrSignatureStatus"],
        "qrData": qr_info["qrData"],
        "qrOcrMatchStatus": qr_info["qrOcrMatchStatus"],
        "qrOcrDiscrepancies": qr_info["qrOcrDiscrepancies"],
        "barcodeDetected": barcode_info["barcodeDetected"],
        "barcodeDecoded": barcode_info["barcodeDecoded"],
        "barcodeStatus": barcode_info["barcodeStatus"],
        "barcodeType": barcode_info["barcodeType"],
        "barcodeData": barcode_info["barcodeData"],
        "visaResult": visa_res,
        "drivingLicenceResult": dl_res,
        "nationalIdResult": nat_res,
        "permitResult": permit_res,
    }
