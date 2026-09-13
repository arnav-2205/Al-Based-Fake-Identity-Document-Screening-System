from app.services.mrz import check_digit, parse_td3

MRZ = (
    "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
    "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
)


def test_check_digit():
    assert check_digit("L898902C3") == 6
    assert check_digit("740812") == 2
    assert check_digit("120415") == 9


def test_parse_valid_mrz():
    parsed = parse_td3(MRZ)
    assert parsed is not None
    assert parsed.surname == "ERIKSSON"
    assert parsed.document_number == "L898902C3"
    assert parsed.checks["documentNumber"] is True
    assert parsed.checks["dateOfBirth"] is True
    assert parsed.checks["expiryDate"] is True


def test_detects_tampered_number():
    tampered = MRZ.replace("L898902C36", "L898902C99")
    parsed = parse_td3(tampered)
    assert parsed.checks["documentNumber"] is False
