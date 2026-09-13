"""ICAO Doc 9303 Complete Multi-Format MRZ Parser (TD1, TD2, TD3).
Parses MRZ strings, extracts structured document fields, and performs
comprehensive check-digit integrity validation.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from ml.mrz.mrz_checksum import verify_check_digit, calculate_check_digit

@dataclass
class ParsedMRZResult:
    format_type: str  # "TD1", "TD2", "TD3"
    document_type: str = ""
    issuing_country: str = ""
    document_number: str = ""
    nationality: str = ""
    date_of_birth: str = ""  # ISO YYYY-MM-DD
    gender: str = ""         # M, F, X, or <
    expiry_date: str = ""    # ISO YYYY-MM-DD
    surname: str = ""
    given_names: str = ""
    optional_data: str = ""
    checks: Dict[str, bool] = field(default_factory=dict)
    all_valid: bool = False
    raw_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format_type,
            "documentType": self.document_type,
            "issuingCountry": self.issuing_country,
            "documentNumber": self.document_number,
            "nationality": self.nationality,
            "dateOfBirth": self.date_of_birth,
            "gender": self.gender,
            "expiryDate": self.expiry_date,
            "surname": self.surname,
            "givenNames": self.given_names,
            "fullName": f"{self.given_names} {self.surname}".strip(),
            "optionalData": self.optional_data,
            "checks": self.checks,
            "allValid": self.all_valid,
            "rawLines": self.raw_lines
        }

def _parse_iso_date(yymmdd: str, is_dob: bool) -> str:
    if not re.fullmatch(r"\d{6}", yymmdd):
        return ""
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    if is_dob:
        century = 1900 if yy > 30 else 2000
    else:
        century = 2000
    try:
        return f"{century + yy:04d}-{mm:02d}-{dd:02d}"
    except ValueError:
        return ""

def parse_mrz(raw_text: str) -> Optional[ParsedMRZResult]:
    """Auto-detects MRZ format (TD1, TD2, or TD3) and parses all fields & checksums."""
    if not raw_text:
        return None
    lines = [re.sub(r"[^A-Z0-9<]", "", ln.upper().strip()) for ln in raw_text.strip().splitlines() if ln.strip()]
    lines = [ln for ln in lines if len(ln) >= 20]
    
    if len(lines) == 3 and all(len(ln) >= 28 for ln in lines):
        return _parse_td1(lines)
    elif len(lines) == 2:
        if max(len(lines[0]), len(lines[1])) >= 40:
            return _parse_td3(lines)
        else:
            return _parse_td2(lines)
    elif len(lines) >= 2:
        # Fallback: check longest two lines
        longest = sorted(lines, key=len, reverse=True)
        if len(longest[0]) >= 40:
            return _parse_td3(longest[:2])
    return None

def _parse_td3(lines: list[str]) -> ParsedMRZResult:
    """TD3 Passport format: 2 lines of 44 chars."""
    l1 = (lines[0] + "<" * 44)[:44]
    l2 = (lines[1] + "<" * 44)[:44]
    
    doc_type = l1[0:2].replace("<", "")
    issuing_country = l1[2:5].replace("<", "")
    
    names = l1[5:44]
    if "<<" in names:
        surname, _, given = names.partition("<<")
    else:
        surname, given = names, ""
    surname = surname.replace("<", " ").strip()
    given = given.replace("<", " ").strip()
    
    doc_num = l2[0:9]
    doc_num_chk = l2[9]
    nationality = l2[10:13].replace("<", "")
    dob = l2[13:19]
    dob_chk = l2[19]
    sex = l2[20]
    expiry = l2[21:27]
    expiry_chk = l2[27]
    optional = l2[28:42]
    optional_chk = l2[42]
    final_chk = l2[43]
    
    comp_str = doc_num + doc_num_chk + dob + dob_chk + expiry + expiry_chk + optional + optional_chk
    
    checks = {
        "documentNumber": verify_check_digit(doc_num, doc_num_chk),
        "dateOfBirth": verify_check_digit(dob, dob_chk),
        "expiryDate": verify_check_digit(expiry, expiry_chk),
        "composite": verify_check_digit(comp_str, final_chk)
    }
    
    all_valid = all(checks.values())
    
    return ParsedMRZResult(
        format_type="TD3",
        document_type=doc_type,
        issuing_country=issuing_country,
        document_number=doc_num.replace("<", ""),
        nationality=nationality,
        date_of_birth=_parse_iso_date(dob, True),
        gender=sex if sex in ("M", "F", "X") else "",
        expiry_date=_parse_iso_date(expiry, False),
        surname=surname,
        given_names=given,
        optional_data=optional.replace("<", ""),
        checks=checks,
        all_valid=all_valid,
        raw_lines=[l1, l2]
    )

def _parse_td1(lines: list[str]) -> ParsedMRZResult:
    """TD1 ID Card format: 3 lines of 30 chars."""
    l1 = (lines[0] + "<" * 30)[:30]
    l2 = (lines[1] + "<" * 30)[:30]
    l3 = (lines[2] + "<" * 30)[:30]
    
    doc_type = l1[0:2].replace("<", "")
    issuing_country = l1[2:5].replace("<", "")
    doc_num = l1[5:14]
    doc_num_chk = l1[14]
    opt1 = l1[15:30]
    
    dob = l2[0:6]
    dob_chk = l2[6]
    sex = l2[7]
    expiry = l2[8:14]
    expiry_chk = l2[14]
    nationality = l2[15:18].replace("<", "")
    opt2 = l2[18:29]
    final_chk = l2[29]
    
    names = l3[0:30]
    if "<<" in names:
        surname, _, given = names.partition("<<")
    else:
        surname, given = names, ""
    surname = surname.replace("<", " ").strip()
    given = given.replace("<", " ").strip()
    
    comp_str = l1[5:30] + l2[0:7] + l2[8:15] + l2[18:29]
    
    checks = {
        "documentNumber": verify_check_digit(doc_num, doc_num_chk),
        "dateOfBirth": verify_check_digit(dob, dob_chk),
        "expiryDate": verify_check_digit(expiry, expiry_chk),
        "composite": verify_check_digit(comp_str, final_chk)
    }
    
    return ParsedMRZResult(
        format_type="TD1",
        document_type=doc_type,
        issuing_country=issuing_country,
        document_number=doc_num.replace("<", ""),
        nationality=nationality,
        date_of_birth=_parse_iso_date(dob, True),
        gender=sex if sex in ("M", "F", "X") else "",
        expiry_date=_parse_iso_date(expiry, False),
        surname=surname,
        given_names=given,
        optional_data=(opt1 + opt2).replace("<", ""),
        checks=checks,
        all_valid=all(checks.values()),
        raw_lines=[l1, l2, l3]
    )

def _parse_td2(lines: list[str]) -> ParsedMRZResult:
    """TD2 format: 2 lines of 36 chars."""
    l1 = (lines[0] + "<" * 36)[:36]
    l2 = (lines[1] + "<" * 36)[:36]
    
    doc_type = l1[0:2].replace("<", "")
    issuing_country = l1[2:5].replace("<", "")
    
    names = l1[5:36]
    if "<<" in names:
        surname, _, given = names.partition("<<")
    else:
        surname, given = names, ""
    surname = surname.replace("<", " ").strip()
    given = given.replace("<", " ").strip()
    
    doc_num = l2[0:9]
    doc_num_chk = l2[9]
    nationality = l2[10:13].replace("<", "")
    dob = l2[13:19]
    dob_chk = l2[19]
    sex = l2[20]
    expiry = l2[21:27]
    expiry_chk = l2[27]
    optional = l2[28:35]
    final_chk = l2[35]
    
    comp_str = doc_num + doc_num_chk + dob + dob_chk + expiry + expiry_chk + optional
    
    checks = {
        "documentNumber": verify_check_digit(doc_num, doc_num_chk),
        "dateOfBirth": verify_check_digit(dob, dob_chk),
        "expiryDate": verify_check_digit(expiry, expiry_chk),
        "composite": verify_check_digit(comp_str, final_chk)
    }
    
    return ParsedMRZResult(
        format_type="TD2",
        document_type=doc_type,
        issuing_country=issuing_country,
        document_number=doc_num.replace("<", ""),
        nationality=nationality,
        date_of_birth=_parse_iso_date(dob, True),
        gender=sex if sex in ("M", "F", "X") else "",
        expiry_date=_parse_iso_date(expiry, False),
        surname=surname,
        given_names=given,
        optional_data=optional.replace("<", ""),
        checks=checks,
        all_valid=all(checks.values()),
        raw_lines=[l1, l2]
    )
