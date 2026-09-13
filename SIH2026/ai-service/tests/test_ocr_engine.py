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
