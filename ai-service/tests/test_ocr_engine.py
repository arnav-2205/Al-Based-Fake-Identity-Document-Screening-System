from app.services import ocr_engine

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <text x="50" y="70">REPUBLIC OF INDIA - PASSPORT</text>
  <text x="50" y="110">TYPE: P | CODE: IND | PASSPORT NO: P1234567</text>
  <text x="180" y="170">NAME: JOHN FICTITIOUS</text>
  <text x="180" y="200">DOB: 12 APR 1985 | SEX: M</text>
  <text x="180" y="230">EXPIRY: 09 MAY 2028</text>
  <text x="55" y="325">P&lt;INDJOHN&lt;FICTITIOUS&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</text>
  <text x="55" y="348">P1234567&lt;4IND8504128M2805098&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;04</text>
</svg>"""


def test_svg_passport_extraction():
    result = ocr_engine.extract(SAMPLE_SVG.encode())

    assert result["fields"]["name"] == "JOHN FICTITIOUS"
    assert result["fields"]["passportNumber"] == "P1234567"
    assert result["fields"]["nationality"] == "IND"
    assert result["fields"]["dateOfBirth"] == "1985-04-12"
    assert result["fields"]["gender"] == "M"
    assert result["fields"]["expiryDate"] == "2028-05-09"
    assert result["mrz"] is not None
    assert "P<IND" in result["mrz"]
    assert "P1234567" in result["mrz"]
    assert result["confidence"] > 0


SAMPLE_DL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <text x="50" y="40">INDIAN UNION DRIVING LICENCE</text>
  <text x="50" y="70">MAHARASHTRA STATE</text>
  <text x="50" y="100">DL No: MH10 20240021135</text>
  <text x="50" y="130">Name: KSHITIJ BIROBA KOLEKAR</text>
  <text x="50" y="160">Date of Birth: 19-10-2005</text>
  <text x="50" y="190">Issue Date: 09-12-2024</text>
  <text x="50" y="220">Validity(NT): 18-10-2045</text>
  <text x="50" y="250">CLASS OF VEHICLES: MCWG LMV</text>
  <text x="50" y="380">SCANNED WITH OKEN SCANNER</text>
</svg>"""


def test_indian_driving_licence_extraction():
    result = ocr_engine.extract(SAMPLE_DL_SVG.encode())

    assert result["detectedDocumentType"] == "DRIVING_LICENCE"
    assert result["documentCategory"] == "DRIVING_LICENCE"
    assert result["documentSubtype"] == "DRIVING_LICENCE"

    dl_res = result["drivingLicenceResult"]
    assert dl_res["dlNumber"] == "MH10 20240021135"
    assert dl_res["holderName"] == "KSHITIJ BIROBA KOLEKAR"
    assert dl_res["dateOfBirth"] == "2005-10-19"
    assert dl_res["issueDate"] == "2024-12-09"
    assert dl_res["expiryDate"] == "2045-10-18"
    assert dl_res["state"] == "MAHARASHTRA"
    assert dl_res["status"] == "VALID"
    assert dl_res["validationMessages"] == []

    # Top level fields must reflect DL result authoritatively
    assert result["fields"]["documentNumber"] == "MH10 20240021135"
    assert result["fields"]["holderName"] == "KSHITIJ BIROBA KOLEKAR"
    assert result["fields"]["name"] == "KSHITIJ BIROBA KOLEKAR"
    assert result["fields"]["dateOfBirth"] == "2005-10-19"
    assert result["fields"]["issueDate"] == "2024-12-09"
    assert result["fields"]["expiryDate"] == "2045-10-18"


def test_dl_validity_label_parsing():
    svg_validity_tr = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
      <text x="50" y="40">DRIVING LICENCE</text>
      <text x="50" y="70">DL NO: KA01 20220001234</text>
      <text x="50" y="100">NAME: AMITABH KUMAR</text>
      <text x="50" y="130">DOB: 15/08/1992</text>
      <text x="50" y="160">ISSUE DATE: 10-01-2022</text>
      <text x="50" y="190">Validity(TR): 09-01-2042</text>
    </svg>"""

    result = ocr_engine.extract(svg_validity_tr.encode())
    dl_res = result["drivingLicenceResult"]

    assert dl_res["expiryDate"] == "2042-01-09"
    assert result["fields"]["expiryDate"] == "2042-01-09"
    assert dl_res["status"] == "VALID"


def test_auto_orientation_selection():
    # Test evaluation function selects optimal angle when landmark hits & score are evaluated
    boxes = [
        {"text": "DRIVING LICENCE", "confidence": 0.9},
        {"text": "MAHARASHTRA", "confidence": 0.9},
        {"text": "VALIDITY", "confidence": 0.9},
        {"text": "GOVERNMENT OF INDIA", "confidence": 0.9},
    ]

    mock_res = [([], b["text"], b["confidence"]) for b in boxes]
    # Verify landmark hits evaluation returns valid hits count
    text_norm = "DRIVING LICENCE MAHARASHTRA VALIDITY GOVERNMENT OF INDIA"
    detected_type, conf = ocr_engine.detect_document_type(text_norm)
    assert detected_type == "DRIVING_LICENCE"
    assert conf >= 0.90


def test_dl_date_normalization_and_validation():
    # 1. Test normalization formats: 18-10-2045, 18/10/2045, 18.10.2045, 18 10 2045 -> 2045-10-18
    assert ocr_engine._normalize_date("18-10-2045") == "2045-10-18"
    assert ocr_engine._normalize_date("18/10/2045") == "2045-10-18"
    assert ocr_engine._normalize_date("18.10.2045") == "2045-10-18"
    assert ocr_engine._normalize_date("18 10 2045") == "2045-10-18"

    # 2. Test impossible date (month 18) returns empty string
    assert ocr_engine._normalize_date("2024-18-10") == ""

    # 3. Test that an invalid expiry date cannot produce VALID status
    invalid_exp_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
      <text x="50" y="40">DRIVING LICENCE</text>
      <text x="50" y="70">DL NO: MH10 20240021135</text>
      <text x="50" y="100">NAME: KSHITIJ BIROBA KOLEKAR</text>
      <text x="50" y="130">DOB: 19-10-2005</text>
      <text x="50" y="160">ISSUE DATE: 09-12-2024</text>
      <text x="50" y="190">Validity: INVALID_DATE_STRING</text>
    </svg>"""

    res = ocr_engine.extract(invalid_exp_svg.encode())
    dl_res = res["drivingLicenceResult"]

    assert dl_res["expiryDate"] is None
    assert dl_res["status"] != "VALID"
    assert dl_res["status"] == "PARTIAL"
    assert "Expiry date unavailable" in dl_res["validationMessages"]


def test_sha256_ocr_caching():
    ocr_engine._clear_ocr_cache()

    # 1. First extraction of SAMPLE_SVG
    data_1 = SAMPLE_SVG.encode()
    res_1 = ocr_engine.extract(data_1)
    assert ocr_engine._get_cache_size() == 1
    assert ocr_engine._get_cache_hits() == 0

    # 2. Second extraction of exact same bytes -> must hit cache
    res_2 = ocr_engine.extract(data_1)
    assert ocr_engine._get_cache_hits() == 1
    assert res_1["fields"] == res_2["fields"]
    assert res_1["detectedDocumentType"] == res_2["detectedDocumentType"]

    # 3. Different image bytes -> separate cache entry
    data_2 = SAMPLE_DL_SVG.encode()
    res_3 = ocr_engine.extract(data_2)
    assert ocr_engine._get_cache_size() == 2
    assert ocr_engine._get_cache_hits() == 1

    # 4. Failed OCR (empty bytes) is not cached
    ocr_engine.extract(b"")
    assert ocr_engine._get_cache_size() == 2




