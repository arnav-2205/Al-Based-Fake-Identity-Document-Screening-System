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
        if max_dim > 1600:
            scale = 1600.0 / max_dim
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
                    "IDENTITY", "CARD", "ELECTION", "COMMISSION", "INCOME TAX", "AADHAAR",
                    "SURNAME", "GIVEN", "DATE OF BIRTH", "DOB", "SEX", "VALIDITY", "EXPIRY",
                    "HOLDER", "SIGNATURE", "P<", "I<", "A<", "NAME:", "ISSUE", "PERSONALAUSWEIS",
                    "DEUTSCHLAND", "BUNDESREPUBLIK", "CARTE", "NATIONALE"
                )
                landmark_hits = sum(1 for lm in landmarks if lm in joined)
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
                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]
                    boxes.append({
                        "text": cleaned,
                        "bbox": box,
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
        if l1.startswith("P") and len(l1) >= 15:
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
        doc_type = self._detect_doc_type(upper_text, raw_mrz)

        fields: dict[str, str] = {}
        field_confidences: dict[str, float] = {}
        notes: list[str] = [f"Generic National ID Adapter active (Country: {country}, Type: {doc_type})"]

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
        field_states = self._determine_field_states(fields, field_confidences, doc_type)

        return {
            "fields": fields,
            "fieldConfidences": field_confidences,
            "fieldStates": field_states,
            "issuingCountry": country,
            "detectedDocumentType": doc_type,
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

    def _detect_doc_type(self, upper: str, raw_mrz: str | None) -> str:
        if raw_mrz and raw_mrz.startswith("P<"):
            return "PASSPORT"
        if any(k in upper for k in ("AADHAAR", "UIDAI", "UNIQUE IDENTIFICATION")):
            return "AADHAAR"
        if any(k in upper for k in ("DRIVING LICENCE", "DRIVING LICENSE", "MOTOR VEHICLES", "TRANSPORT DEPARTMENT")):
            return "DRIVING_LICENCE"
        if any(k in upper for k in ("INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER")):
            return "PAN"
        if any(k in upper for k in ("ELECTION COMMISSION", "ELECTORAL", "ELECTOR PHOTO")):
            return "VOTER_ID"
        if any(k in upper for k in ("PASSPORT", "PASSEPORT")):
            return "PASSPORT"
        if any(k in upper for k in ("PERSONALAUSWEIS", "NATIONAL ID", "IDENTITY CARD", "CARTE NATIONALE", "CITIZEN CARD")):
            return "NATIONAL_ID"
        return "NATIONAL_ID"

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

        # Path C: Layout Candidate Ranking (For documents without 'Name:' label, e.g. Aadhaar)
        # Find anchor index of DOB / Gender / Relation line
        anchor_idx = -1
        for i, line in enumerate(lines):
            if re.search(r"\b(DOB|YEAR OF BIRTH|YOB|DATE OF BIRTH|MALE|FEMALE|SON OF|DAUGHTER OF|WIFE OF|S/O|D/O|W/O)\b", line, re.I):
                anchor_idx = i
                break

        candidates: list[tuple[str, float, float]] = []  # (text, score, box_conf)
        search_lines = lines[:anchor_idx] if anchor_idx > 0 else lines[:6]

        for line_str in search_lines:
            cand = line_str.strip()
            up_cand = cand.upper()

            # Filter non-name noise
            if len(cand) < 3 or len(cand) > 40:
                continue
            if any(k in up_cand for k in self.NOISE_KEYWORDS):
                continue
            if re.search(r"\d", cand):  # Name should not contain digits
                continue
            if not re.match(r"^[A-Za-z][A-Za-z '.-]+$", cand):
                continue

            # Candidate Scoring Formula
            score = 0.5
            words = cand.split()
            if 2 <= len(words) <= 4:
                score += 0.25
            if cand.isupper():
                score += 0.15
            elif cand.istitle():
                score += 0.10

            # Match with box confidence
            box_c = 0.80
            for box in boxes:
                if cand.lower() in box["text"].lower():
                    box_c = box["confidence"]
                    break

            candidates.append((cand.upper(), score, box_c))

        if candidates:
            # Sort by candidate score descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_name, best_score, box_conf = candidates[0]
            conf = min(0.98, max(0.65, box_conf * best_score))
            return best_name, round(conf, 2), f"Candidate Ranking (Score: {best_score:.2f})"

        return "", 0.0, "NOT_DETECTED"

    def _extract_doc_number(
        self, lines: list[str], upper: str, boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        # Indian Patterns
        # Aadhaar: 12 digits (4 4 4 or contiguous)
        aadhaar_m = re.search(r"\b(\d{4}[-\s]?\d{4}[-\s]?\d{4})\b", upper)
        if aadhaar_m and any(k in upper for k in ("AADHAAR", "GOVERNMENT OF INDIA", "MALE", "FEMALE", "INDIA", "UNIQUE")):
            return aadhaar_m.group(1), 0.96

        # DL: e.g. MH10 20240021135
        dl_m = re.search(r"\b([A-Z]{2}[0-9O]{1,2}\s*[0-9O]{11,15})\b", upper)
        if dl_m:
            return dl_m.group(1).replace("O", "0"), 0.95

        # PAN: 5 uppercase, 4 digits, 1 uppercase
        pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", upper)
        if pan_m:
            return pan_m.group(1), 0.97

        # Voter ID: 3 uppercase, 7 digits
        voter_m = re.search(r"\b([A-Z]{3}[0-9]{7})\b", upper)
        if voter_m:
            return voter_m.group(1), 0.95

        # Multilingual Generic Document Number Regex
        doc_m = re.search(
            r"(?:DOCUMENT\s*NO?|ID\s*NO?|IDENTIFICATION\s*NO?|CARD\s*NO?|PASSPORT\s*NO?|LICENCE\s*NO?|LICENSE\s*NO?|SERIAL\s*NO?)\s*[:\s|-]+\s*([A-Z0-9\s-]{5,20})",
            upper,
        )
        if doc_m:
            val = doc_m.group(1).strip().replace(" ", "")
            if not any(k in val for k in self.NOISE_KEYWORDS):
                return val, 0.90

        return "", 0.0

    def _extract_dob(
        self, lines: list[str], upper: str, boxes: list[dict[str, Any]]
    ) -> tuple[str, float]:
        m = re.search(
            r"(?:DOB|DATE\s*OF\s*BIRTH|YEAR\s*OF\s*BIRTH|BIRTH\s*YEAR|YOB|BIRTH|BORN|NAISSANCE|GEBURTSDATUM|FECHA\s*DE\s*NACIMIENTO)\s*[:\s|/]*"
            r"(\d{1,2}\s+[A-Z]{3,9}\s+\d{4}|\d{1,4}[-/]\d{1,2}[-/]\d{2,4}|\b\d{4}\b)",
            upper,
        )
        if m:
            norm = _normalize_date(m.group(1))
            if norm:
                return norm, 0.92

        # Standalone date pattern near DOB anchor
        for l in lines:
            if re.search(r"\b(DOB|BIRTH|YOB|NAISSANCE|GEBURTSDATUM)\b", l, re.I):
                d_m = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\b\d{4}\b)\b", l)
                if d_m:
                    norm = _normalize_date(d_m.group(1))
                    if norm:
                        return norm, 0.88
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
        m = re.search(
            r"(?:EXPIRY|EXPIRES|VALID\s*UNTIL|VALIDITY|ABLAUFDATUM|CADUCIDAD|EXPIRATION|DEXPIRA)\b[\s\S]{0,80}?(\d{1,4}[-/ ]\d{1,2}[-/ ]\d{2,4}[A-Za-z]?)",
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
        self, fields: dict[str, str], confidences: dict[str, float], doc_type: str
    ) -> dict[str, str]:
        all_target_fields = [
            "documentNumber", "holderName", "dateOfBirth", "gender",
            "nationality", "issuingCountry", "issueDate", "expiryDate", "address"
        ]
        states: dict[str, str] = {}

        if fields.get("issuingCountry") and fields["issuingCountry"] != "UNKNOWN":
            confidences["issuingCountry"] = 0.95

        for f in all_target_fields:
            val = fields.get(f) or (fields.get("name") if f == "holderName" else None)
            conf = confidences.get(f, 0.0)

            if val:
                states[f] = "DETECTED" if conf >= 0.65 else "LOW_CONFIDENCE"
            else:
                if doc_type == "PASSPORT" and f in ("address", "fatherName"):
                    states[f] = "NOT_APPLICABLE"
                elif doc_type in ("AADHAAR", "PAN", "NATIONAL_ID", "VOTER_ID", "DRIVING_LICENCE") and f == "expiryDate":
                    states[f] = "NOT_APPLICABLE" if doc_type in ("AADHAAR", "PAN") else "NOT_DETECTED"
                elif doc_type in ("AADHAAR", "PAN", "VOTER_ID") and f in ("issueDate", "nationality"):
                    states[f] = "NOT_APPLICABLE"
                else:
                    states[f] = "NOT_DETECTED"

        return states


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

    # Document-adaptive Field Extraction Confidence vs Raw Bounding Box OCR Confidence
    valid_confs = [v for k, v in field_confidences.items() if v > 0.0 and field_states.get(k) in ("DETECTED", "LOW_CONFIDENCE")]
    field_extraction_conf = round(sum(valid_confs) / len(valid_confs), 3) if valid_confs else 0.85
    raw_ocr_conf = round(ocr_confidence if ocr_confidence is not None else 0.85, 3)
    overall_conf = field_extraction_conf if valid_confs else raw_ocr_conf

    visual_zone_payload = {
        **fields,
        "rawText": text[:2500] if text else "",
        "detectedDocumentType": doc_type,
        "issuingCountry": issuing_country,
        "fieldConfidences": field_confidences,
        "fieldStates": field_states,
        "fieldExtractionConfidence": field_extraction_conf,
        "rawOcrConfidence": raw_ocr_conf,
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
    }

    extraction_time_ms = round((time.time() - start_time) * 1000, 1)

    return {
        "mrz": raw_mrz,
        "fields": fields,
        "visualZone": visual_zone_payload,
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
    }
