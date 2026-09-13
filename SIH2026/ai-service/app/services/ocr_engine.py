"""OCR + MRZ extraction service.

Extracts printed text, Machine Readable Zone (MRZ) lines, and Visual Inspection Zone (VIZ) fields
from uploaded images and vector documents. Uses EasyOCR / regex / SVG text parser and ICAO 9303 TD3 parser.
"""
from __future__ import annotations

import html
import io
import re
import time
from datetime import datetime

from PIL import Image, ImageEnhance, ImageFilter

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


def _extract_text_from_data(data: bytes) -> tuple[str, float | None, list[tuple[list, str]]]:
    """Return extracted text, optional EasyOCR mean confidence, and per-line
    (bbox, text) boxes for layout-aware field extraction (bitmap OCR only)."""
    lines: list[str] = []
    ocr_confidence: float | None = None

    # 1. Try decoding as UTF-8 / SVG text
    try:
        text_content = data.decode("utf-8", errors="ignore")
        lower = text_content.lower()
        if "<svg" in lower or "passport" in lower or "<text" in lower:
            extracted_tags = re.findall(r">([^<]+)<", text_content)
            for tag in extracted_tags:
                cleaned = html.unescape(tag.strip())
                if cleaned:
                    lines.append(cleaned)
            if lines:
                return "\n".join(lines), None, []
    except Exception:
        pass

    # 2. Try EasyOCR for bitmap images (JPG/PNG/WebP) with automatic orientation detection
    try:
        import numpy as np  # noqa: PLC0415

        img = Image.open(io.BytesIO(data)).convert("RGB")
        # Resize huge images (e.g. 4000x3000 phone camera captures) to max 1600px
        # for dramatically faster OCR inference without degrading character accuracy
        max_dim = max(img.width, img.height)
        if max_dim > 1600:
            scale = 1600.0 / max_dim
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        elif max_dim < 450:
            scale = 650.0 / max(max_dim, 1)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.BICUBIC)

        # Enhance contrast and sharpness slightly to eliminate background guilloche noise
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
                    "HOLDER", "SIGNATURE", "P<", "I<", "A<", "NAME:", "ISSUE"
                )
                landmark_hits = sum(1 for lm in landmarks if lm in joined)
                score = sum(len(t) for _, t, c in res if len(t) >= 4 and c >= 0.4)
                return landmark_hits, score

            hits, score = eval_orientation(result)
            # A document is ONLY confirmed upright at 0-deg if it has at least 2 strong document landmarks.
            # Otherwise (e.g. rotated mobile photos or scans with vertical garbage text), test 90, 270, 180.
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
                        # Early break: as soon as we find a confident upright rotation with >= 2 landmarks, stop!
                        if rot_hits >= 2:
                            break
                result = best_res

            confidences: list[float] = []
            boxes: list[tuple[list, str]] = []
            for (box, text, conf) in result:
                cleaned = text.strip()
                if cleaned:
                    lines.append(cleaned)
                    confidences.append(float(conf))
                    boxes.append((box, cleaned))
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
    # Extract date substring if embedded with other words
    m = re.search(r"\b(\d{4}[-/]\d{2}[-/]\d{2})\b", raw)
    if m:
        return m.group(1).replace("/", "-")
    m = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b", raw)
    if m:
        raw = m.group(1)
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


def _find_mrz(text: str) -> str | None:
    text = _normalize_text(text)
    lines = text.splitlines()
    cleaned = [_clean_mrz_candidate(l) for l in lines]
    # Filter candidates: an MRZ line MUST have at least 20 chars and at least 2 '<' fillers
    cleaned = [l for l in cleaned if len(l) >= 20 and l.count("<") >= 2]

    # 1. Look for TD3 (Passports: 2 lines, 44 chars each)
    for i, l1 in enumerate(cleaned):
        if l1.startswith("P<") or (len(l1) >= 4 and l1[0] == "P" and "<" in l1[:6]):
            for j in range(i + 1, min(i + 4, len(cleaned))):
                l2 = cleaned[j]
                # Line 2 typically has document number, digits, and filler chars
                if len(l2) >= 25 and any(c.isdigit() for c in l2):
                    return (l1 + "<" * 44)[:44] + "\n" + (l2 + "<" * 44)[:44]
            if len(l1) >= 30:
                return (l1 + "<" * 44)[:44]

    # 2. Look for TD1 (ID cards: 3 lines, 30 chars each)
    for i, l1 in enumerate(cleaned):
        if any(l1.startswith(p) for p in ("I<", "A<", "C<", "ID<")) and i + 2 < len(cleaned):
            l2 = cleaned[i + 1]
            l3 = cleaned[i + 2]
            if len(l2) >= 20 and len(l3) >= 20:
                return (l1 + "<" * 30)[:30] + "\n" + (l2 + "<" * 30)[:30] + "\n" + (l3 + "<" * 30)[:30]

    return None


def _layout_parse_viz(boxes: list[tuple[list, str]]) -> dict[str, str]:
    """Spatial label -> value pairing using OCR box positions.

    Supports both:
    1. Value placed directly below the label (common in passports/IDs).
    2. Value placed to the right of the label on the same row.
    """
    if not boxes:
        return {}

    items = []
    for bbox, text in boxes:
        cleaned = text.strip()
        if not cleaned:
            continue
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        items.append({
            "text": cleaned,
            "xmin": min(xs), "ymin": min(ys),
            "xmax": max(xs), "ymax": max(ys),
            "cx": sum(xs) / len(xs), "cy": sum(ys) / len(ys),
            "h": max(ys) - min(ys), "w": max(xs) - min(xs),
        })

    fields: dict[str, str] = {}

    def get_candidate(label_pat, exclude_pat=None):
        lbl = next((it for it in items if re.search(label_pat, it["text"], re.I)), None)
        if not lbl:
            return None
        clean_lbl = lbl["text"].strip(" :|-")
        noise_keywords = ("PASSEPORT", "PASSEFORT", "PASSPORT", "DOCUMENT", "NOM", "PRENOM", "NAISSANCE", "DELIVRANCE", "SIGNATURE", "HOLDER", "NODU", "NUMERO", "COUNTRY", "PAYS", "TYPE")
        if ":" in clean_lbl:
            parts = clean_lbl.split(":", 1)
            cand = parts[1].strip(" /|-")
            clean_c = re.sub(r"[^A-Z0-9]", "", cand.upper())
            if not any(k in clean_c for k in noise_keywords):
                if len(cand) >= 2 and not (exclude_pat and re.search(exclude_pat, cand, re.I)):
                    return cand

        # Below: y distance 5..55 px, left-aligned within 70px or center-aligned within 100px
        below = [
            it for it in items
            if 5 < it["ymin"] - lbl["ymin"] < 55 and abs(it["xmin"] - lbl["xmin"]) < 70
        ]
        # Right: same horizontal line (cy diff < 15), to the right (5 < xdiff < 280)
        right = [
            it for it in items
            if abs(it["cy"] - lbl["cy"]) < 15 and 5 < it["xmin"] - lbl["xmax"] < 280
        ]
        cands = below + right
        for c in cands:
            val = c["text"].strip(" :|-")
            clean_v = re.sub(r"[^A-Z0-9]", "", val.upper())
            if not val or re.search(label_pat, val, re.I) or any(k in clean_v for k in noise_keywords):
                continue
            if exclude_pat and re.search(exclude_pat, val, re.I):
                continue
            return val
        return None

    surname = get_candidate(r"\b(SURNAME|NOM)\b")
    given = get_candidate(r"\b(GIVEN\s*NAMES?|PRENOMS?|FIRST\s*NAME)\b")
    full_name = get_candidate(r"\b(FULL\s*NAME|NAME|HOLDER)\b")

    if given and surname:
        fields["name"] = f"{given} {surname}".upper()
    elif surname:
        fields["name"] = surname.upper()
    elif given:
        fields["name"] = given.upper()
    elif full_name:
        fields["name"] = full_name.upper()

    doc_num = get_candidate(r"(?:PASSPORT\s*NO?|PASSPORTNO|PASSEPORT|DOCUMENT\s*NO?|DOC\s*NO|LICENCE\s*NO)")
    if doc_num:
        doc_num = doc_num.upper().replace(" ", "")
        noise_num = ("NODU", "PASSEPORT", "PASSEFORT", "PASSPORT", "REPUBLIC", "GOVERNMENT", "PAYS", "CODE", "TYPE", "DOCUMENT")
        if not any(k in doc_num for k in noise_num):
            if len(doc_num) == 8 and doc_num[0] == "2" and doc_num[1:].isdigit():
                doc_num = "Z" + doc_num[1:]
            fields["passportNumber"] = doc_num
            fields["documentNumber"] = doc_num

    nat = get_candidate(r"\b(NATIONALITY|NATIONALITE|COUNTRY\s*CODE)\b")
    if nat:
        m = re.search(r"\b([A-Z]{3})\b", nat.upper())
        if m:
            fields["nationality"] = m.group(1)

    dob = get_candidate(r"\b(DATE\s*OF\s*BIRTH|DOB|BIRTH|NAISSANCE)\b")
    if dob:
        norm_dob = _normalize_date(dob)
        if norm_dob:
            fields["dateOfBirth"] = norm_dob

    sex = get_candidate(r"\b(SEX|GENDER|SEXE)\b")
    if sex:
        sex_up = sex.upper()
        if "M" in sex_up:
            fields["gender"] = "M"
        elif "F" in sex_up:
            fields["gender"] = "F"

    issue = get_candidate(r"\b(DATE\s*OF\s*ISSUE|ISSUE\s*DATE|ISSUED|DATE.*DELIVRANCE)\b", exclude_pat=r"PLACE")
    if issue:
        norm_issue = _normalize_date(issue)
        if norm_issue:
            fields["issueDate"] = norm_issue

    expiry = get_candidate(r"\b(DATE\s*OF\s*EXPIRY|EXPIRY|EXPIRES|VALID\s*UNTIL|DEXPIRA)\b")
    if expiry:
        norm_exp = _normalize_date(expiry)
        if norm_exp:
            fields["expiryDate"] = norm_exp

    return fields


def _parse_viz_fallback(text: str) -> dict[str, str]:
    text = _normalize_text(text)
    upper = text.upper()
    fields: dict[str, str] = {}

    # 1. Name:
    # Priority A: Labeled name (e.g. Name: KSHITIJ BIROBA KOLEKAR)
    name_m = re.search(r"(?:NAME|FULL\s*NAME|HOLDER(?:'S)?\s*NAME)\s*[:\s|]+\n*([A-Z][A-Za-z '.-]{2,40})", text, re.I)
    if name_m:
        cand = name_m.group(1).splitlines()[0].strip()
        if not any(w in cand.upper() for w in ("SIGNATURE", "HOLDER", "DATE", "DOB", "ADDRESS", "OFFICIAL", "REPUBLIC", "GOVERNMENT", "UNION", "DRIVING")):
            fields["name"] = cand.upper()

    # Priority B: Surname + Given name
    if not fields.get("name"):
        surname_m = re.search(r"(?:SURNAME|NOM)\s*[:\s|]+([A-Z][A-Za-z '.-]{1,30})", upper)
        given_m = re.search(r"(?:GIVEN\s*NAMES?|PRENOMS?)\s*[:\s|]+([A-Z][A-Za-z '.-]{1,30})", upper)
        if surname_m and given_m:
            s = surname_m.group(1).splitlines()[0].strip()
            g = given_m.group(1).splitlines()[0].strip()
            fields["name"] = f"{g} {s}".upper()
        elif surname_m:
            fields["name"] = surname_m.group(1).splitlines()[0].strip().upper()
        elif given_m:
            fields["name"] = given_m.group(1).splitlines()[0].strip().upper()

    # 2. Document Number:
    # Check Indian Driving Licence: e.g. MH10 20240021135, DL04...
    dl_m = re.search(r"\b([A-Z]{2}[0-9O]{1,2}\s*[0-9O]{11,15})\b", upper)
    # Check PAN: 5 uppercase letters, 4 digits, 1 uppercase letter
    pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", upper)
    # Check Aadhaar: 12 digits (often grouped 4 4 4)
    aadhaar_m = re.search(r"\b(\d{4}\s\d{4}\s\d{4})\b", text)
    # Check Voter ID (EPIC): 3 uppercase letters, 7 digits
    voter_m = re.search(r"\b([A-Z]{3}[0-9]{7})\b", upper)

    if dl_m:
        doc_num = dl_m.group(1).replace("O", "0")
        fields["passportNumber"] = doc_num
        fields["documentNumber"] = doc_num
    elif pan_m and ("INCOME" in upper or "PERMANENT" in upper or "PAN" in upper):
        doc_num = pan_m.group(1)
        fields["passportNumber"] = doc_num
        fields["documentNumber"] = doc_num
    elif aadhaar_m and ("AADHAAR" in upper or "GOVERNMENT" in upper or "MALE" in upper or "FEMALE" in upper):
        doc_num = aadhaar_m.group(1)
        fields["passportNumber"] = doc_num
        fields["documentNumber"] = doc_num
    elif voter_m and ("ELECTION" in upper or "ELECTOR" in upper):
        doc_num = voter_m.group(1)
        fields["passportNumber"] = doc_num
        fields["documentNumber"] = doc_num
    else:
        # Check standard passport number or generic document number
        doc_match = re.search(
            r"(?:PASSPORT\s*(?:NO|NUMBER)?|DOCUMENT\s*(?:NO|NUMBER)?|PASSEPORT|LICENCE\s*NO|LICENSE\s*NO)\s*[:\s|]+([A-Z0-9\s]{6,16})",
            upper,
        )
        if not doc_match:
            doc_match = re.search(
                r"(?:PASSPORT\s*NO?|PASSPORTNO|DOC\s*NO)[^\n]*\n+([A-Z0-9]{6,12})",
                upper,
            )
        if doc_match:
            doc_num = doc_match.group(1).strip().upper().replace(" ", "")
            if not any(w in doc_num for w in ("REPUBLIC", "GOVERNMENT", "PASSPORT", "INDIA", "SCANNER", "OKEN")):
                if len(doc_num) == 8 and doc_num[0] == "2" and doc_num[1:].isdigit():
                    doc_num = "Z" + doc_num[1:]
                fields["passportNumber"] = doc_num
                fields["documentNumber"] = doc_num

    # 3. Nationality:
    nat_match = re.search(r"(?:NATIONALITY|NAT(?:IONALITY)?|CITIZENSHIP)\s*[:\s|]+([A-Z]{3})", upper)
    if nat_match:
        fields["nationality"] = nat_match.group(1).strip().upper()
    elif any(w in upper for w in ("INDIAN", "MAHARASHTRA", "GOVERNMENT OF INDIA", "REPUBLIC OF INDIA")):
        fields["nationality"] = "IND"

    # 4. Date of Birth:
    dob_match = re.search(
        r"(?:DOB|DATE\s*OF\s*BIRTH|BIRTH\s*DATE|BIRTH|BORN|NAISSANCE)\s*[:\s|]+"
        r"(\d{1,2}\s+[A-Z]{3,9}\s+\d{4}|\d{1,4}[-/]\d{1,2}[-/]\d{2,4})",
        upper,
    )
    if not dob_match:
        dob_match = re.search(
            r"(?:DOB|BIRTH|BORN|NAISSANCE)[^\n]*\n+.*?(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})",
            upper,
        )
    if dob_match:
        fields["dateOfBirth"] = _normalize_date(dob_match.group(1).strip())

    # 5. Gender:
    gender_match = re.search(r"(?:SEX|GENDER)\s*[:\s|]+(M|F|MALE|FEMALE)", upper)
    if gender_match:
        val = gender_match.group(1).strip().upper()
        fields["gender"] = "M" if val.startswith("M") else "F"
    elif re.search(r"\bSon\s*(?:of)?\b", text, re.I):
        fields["gender"] = "M"
    elif re.search(r"\b(?:Daughter|Wife)\s*(?:of)?\b", text, re.I):
        fields["gender"] = "F"

    # 6. Issue Date:
    issue_match = re.search(
        r"(?:ISSUE\s*DATE|DATE\s*OF\s*ISSUE|DATE\s*OF\s*FIRST\s*ISSUE|ISSUED\s*ON|ISSUED)\b[\s\S]{0,100}?(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})",
        upper,
    )
    if issue_match:
        fields["issueDate"] = _normalize_date(issue_match.group(1).strip())

    # 7. Expiry Date / Validity:
    # First check driving licence validity patterns e.g. Validity(NT) 18 10 204s or Valid Till DD-MM-YYYY
    dl_valid_m = re.search(
        r"(?:Validity(?:\([A-Z]+\))?|Valid\s*Till|Valid\s*Upto)[\s\S]{0,80}?(\d{1,2}[\s\-\/]\d{1,2}[\s\-\/](?:\d{4}|\d{3}[A-Za-z]))",
        text,
        re.I,
    )
    if dl_valid_m:
        raw_val = dl_valid_m.group(1).strip()
        # Clean OCR digit errors like '204s' -> '2045'
        if len(raw_val) >= 4 and raw_val[-1].lower() == "s":
            raw_val = raw_val[:-1] + "5"
        raw_val = raw_val.replace(" ", "-")
        norm_v = _normalize_date(raw_val)
        if norm_v:
            fields["expiryDate"] = norm_v

    if not fields.get("expiryDate"):
        expiry_match = re.search(
            r"(?:EXPIRY|EXPIRES|EXPIRATION|VALID\s*UNTIL|VALIDITY|VALID\s*UPTO|DATE\s*OF\s*EXPIRY|DEXPIRA)\b[\s\S]{0,100}?(\d{1,4}[-/ ]\d{1,2}[-/ ]\d{2,4}[A-Za-z]?)",
            upper,
        )
        if expiry_match:
            raw_exp = expiry_match.group(1).strip().replace("s", "5").replace("S", "5").replace(" ", "-")
            fields["expiryDate"] = _normalize_date(raw_exp)

    # Sanity check: Expiry date should not be the exact same as Issue date when later dates exist in the document
    if fields.get("issueDate") and fields.get("expiryDate") == fields.get("issueDate"):
        # Look for subsequent future dates in text
        all_found = re.findall(r"\b(\d{1,2}[\s\-\/]\d{1,2}[\s\-\/](?:\d{4}|\d{3}[A-Za-z]))\b", text)
        for cand_raw in all_found:
            clean_cand = cand_raw.replace("s", "5").replace("S", "5").replace(" ", "-")
            norm_cand = _normalize_date(clean_cand)
            if norm_cand and norm_cand > fields["issueDate"]:
                fields["expiryDate"] = norm_cand
                break

    # 8. Extra Visual Fields: Father/Spouse & Address
    rel_m = re.search(r"(?:Son\s*\/\s*Daughter\s*\/\s*Wife\s*of|Father(?:'s)?\s*Name|S\/O|D\/O|W\/O)\s*[:\s|]+\n*([A-Z][A-Za-z '.-]{2,40})", text, re.I)
    if rel_m:
        fields["fatherName"] = rel_m.group(1).strip().upper()

    addr_m = re.search(r"Address\s*[:\s|]+\n*([^\n]+(?:\n[^\n]+){0,2})", text, re.I)
    if addr_m:
        cleaned_addr = " ".join(addr_m.group(1).split()).strip()
        if len(cleaned_addr) > 5:
            fields["address"] = cleaned_addr

    return fields


def _compute_confidence(
    fields: dict[str, str],
    mrz_valid: bool,
    text_present: bool,
    ocr_confidence: float | None,
) -> float:
    if ocr_confidence is not None:
        base = max(0.0, min(1.0, ocr_confidence))
    elif text_present:
        base = 0.75
    else:
        return 0.0

    keys = ("name", "passportNumber", "nationality", "dateOfBirth", "gender", "expiryDate")
    filled = sum(1 for k in keys if fields.get(k))
    field_boost = (filled / len(keys)) * 0.15
    mrz_boost = 0.1 if mrz_valid else 0.0
    return round(min(1.0, base + field_boost + mrz_boost), 3)


def extract(data: bytes) -> dict:
    start_time = time.time()
    notes: list[str] = []
    raw_mrz: str | None = None

    text, ocr_confidence, boxes = _extract_text_from_data(data)
    if text:
        notes.append("OCR: Real-Time Text & Spatial Vector Extraction")
        raw_mrz = _find_mrz(text)
    else:
        notes.append("OCR: No readable text detected in uploaded document")

    viz_fields = _parse_viz_fallback(text) if text else {}
    layout_fields = _layout_parse_viz(boxes)
    if layout_fields:
        notes.append("VIZ: Layout-aware spatial field extraction")
        viz_fields = {**viz_fields, **{k: v for k, v in layout_fields.items() if v}}

    # Try TD3 (Passport: 2x44) first, then TD1 (ID Card: 3x30)
    parsed = mrz_mod.parse_td3(raw_mrz) if raw_mrz else None
    if not parsed and raw_mrz and raw_mrz.count("\n") >= 2:
        parsed = mrz_mod.parse_td1(raw_mrz)

    fields: dict[str, str] = {}
    checks: dict[str, bool] = {}
    mrz_valid = False

    if parsed and parsed.all_valid:
        # Genuine validated MRZ
        name = f"{parsed.given_names} {parsed.surname}".strip()
        fields = {
            "name": name or viz_fields.get("name", ""),
            "passportNumber": parsed.document_number or viz_fields.get("passportNumber", ""),
            "documentNumber": parsed.document_number or viz_fields.get("documentNumber", ""),
            "nationality": parsed.nationality or viz_fields.get("nationality", ""),
            "dateOfBirth": parsed.date_of_birth or viz_fields.get("dateOfBirth", ""),
            "gender": parsed.sex or viz_fields.get("gender", ""),
            "issueDate": viz_fields.get("issueDate", ""),
            "expiryDate": parsed.expiry_date or viz_fields.get("expiryDate", ""),
        }
        checks = parsed.checks
        mrz_valid = True
        notes.append("MRZ: Validated ICAO Checkdigits (100% Integrity)")
    elif parsed:
        # MRZ present with minor checkdigit disparity: prioritize cross-referenced fields
        mrz_name = f"{parsed.given_names} {parsed.surname}".strip()
        fields = {
            "name": viz_fields.get("name") or mrz_name,
            "passportNumber": viz_fields.get("passportNumber") or parsed.document_number,
            "documentNumber": viz_fields.get("documentNumber") or parsed.document_number,
            "nationality": viz_fields.get("nationality") or parsed.nationality,
            "dateOfBirth": viz_fields.get("dateOfBirth") or parsed.date_of_birth,
            "gender": viz_fields.get("gender") or parsed.sex,
            "issueDate": viz_fields.get("issueDate", ""),
            "expiryDate": viz_fields.get("expiryDate") or parsed.expiry_date,
        }
        checks = parsed.checks
        mrz_valid = any(checks.values()) and checks.get("documentNumber", False)
        notes.append("MRZ: Checkdigit mismatch cross-referenced with Visual Zone")
    else:
        # Clean VIZ document (Driving Licence, Aadhaar, PAN, Voter ID, or non-MRZ ID)
        fields = {
            "name": viz_fields.get("name", ""),
            "passportNumber": viz_fields.get("passportNumber", ""),
            "documentNumber": viz_fields.get("documentNumber", ""),
            "nationality": viz_fields.get("nationality", ""),
            "dateOfBirth": viz_fields.get("dateOfBirth", ""),
            "gender": viz_fields.get("gender", ""),
            "issueDate": viz_fields.get("issueDate", ""),
            "expiryDate": viz_fields.get("expiryDate", ""),
        }
        if fields.get("name") or fields.get("passportNumber"):
            notes.append("VIZ: Extracted printed document fields")
        elif text:
            notes.append("OCR: Text extracted but no standard fields identified")

    # Classify detected document type
    upper_text = text.upper() if text else ""
    doc_type = "PASSPORT" if (raw_mrz and raw_mrz.startswith("P<")) else "UNKNOWN"
    if doc_type == "UNKNOWN":
        if any(k in upper_text for k in ("DRIVING LICENCE", "DRIVING LICENSE", "MOTOR VEHICLES", "TRANSPORT DEPARTMENT", "VALIDITY(NT)")) or (fields.get("documentNumber") and re.search(r"^[A-Z]{2}[0-9]{2}", fields.get("documentNumber", ""))):
            doc_type = "DRIVING_LICENCE"
        elif any(k in upper_text for k in ("AADHAAR", "UIDAI", "UNIQUE IDENTIFICATION")) or (fields.get("documentNumber") and re.search(r"^\d{4}\s\d{4}\s\d{4}$", fields.get("documentNumber", ""))):
            doc_type = "AADHAAR"
        elif any(k in upper_text for k in ("INCOME TAX DEPARTMENT", "PERMANENT ACCOUNT NUMBER")) or (fields.get("documentNumber") and re.search(r"^[A-Z]{5}[0-9]{4}[A-Z]$", fields.get("documentNumber", ""))):
            doc_type = "PAN"
        elif any(k in upper_text for k in ("ELECTION COMMISSION", "ELECTORAL", "ELECTOR PHOTO")) or (fields.get("documentNumber") and re.search(r"^[A-Z]{3}[0-9]{7}$", fields.get("documentNumber", ""))):
            doc_type = "VOTER_ID"
        elif any(k in upper_text for k in ("PASSPORT", "PASSEPORT", "REPUBLIC OF INDIA - PASSPORT")):
            doc_type = "PASSPORT"
        elif any(k in upper_text for k in ("IDENTITY", "NATIONAL ID", "CITIZEN CARD")):
            doc_type = "NATIONAL_ID"
        elif fields.get("passportNumber") or fields.get("name"):
            doc_type = "NATIONAL_ID"

    # Merge extra visual fields
    vz_payload = {
        **fields,
        "rawText": text[:2500] if text else "",
        "detectedDocumentType": doc_type,
    }
    if viz_fields.get("fatherName"):
        vz_payload["fatherName"] = viz_fields["fatherName"]
    if viz_fields.get("address"):
        vz_payload["address"] = viz_fields["address"]

    confidence = _compute_confidence(fields, mrz_valid, bool(text), ocr_confidence)
    extraction_time_ms = round((time.time() - start_time) * 1000, 1)

    return {
        "mrz": raw_mrz,
        "fields": fields,
        "visualZone": vz_payload,
        "confidence": confidence,
        "mrzValid": mrz_valid,
        "mrzChecks": checks,
        "notes": notes,
        "detectedDocumentType": doc_type,
        "extractionTimeMs": extraction_time_ms,
    }
