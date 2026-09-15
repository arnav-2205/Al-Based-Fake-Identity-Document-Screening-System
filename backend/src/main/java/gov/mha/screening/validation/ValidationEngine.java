package gov.mha.screening.validation;

import gov.mha.screening.ai.AiDtos;
import gov.mha.screening.extraction.ExtractedData;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Deterministic validation (Spec Part 5, step 6). No ML.
 * Covers fraud cases #4 (DOB modification), #5 (passport-number manipulation),
 * #10 (expired document), #12 (MRZ vs visual-zone mismatch).
 */
@Service
public class ValidationEngine {

    public record Outcome(
            boolean failed,
            String status,             // PASS | FAIL
            List<String> reasons,
            boolean mrzChecksumFailed,
            boolean expired,
            boolean crossZoneMismatch
    ) {}

    public Outcome validate(ExtractedData data, AiDtos.OcrResult ocr) {
        List<String> reasons = new ArrayList<>();
        boolean mrzChecksumFailed = false;
        boolean expired = false;
        boolean crossZoneMismatch = false;

        String cat = ocr != null && ocr.documentCategory() != null ? ocr.documentCategory()
                : (data.getVisualZone() != null && data.getVisualZone().get("documentCategory") != null ? String.valueOf(data.getVisualZone().get("documentCategory")) : null);
        String sub = ocr != null && ocr.documentSubtype() != null ? ocr.documentSubtype()
                : (data.getVisualZone() != null && data.getVisualZone().get("documentSubtype") != null ? String.valueOf(data.getVisualZone().get("documentSubtype")) : null);
        String detectedType = ocr != null && ocr.detectedDocumentType() != null ? ocr.detectedDocumentType()
                : (data.getVisualZone() != null && data.getVisualZone().get("detectedDocumentType") != null ? String.valueOf(data.getVisualZone().get("detectedDocumentType")) : null);

        boolean hasClassification = (cat != null && !"UNKNOWN".equalsIgnoreCase(cat))
                || (sub != null && !"UNKNOWN".equalsIgnoreCase(sub))
                || (detectedType != null && !"UNKNOWN".equalsIgnoreCase(detectedType));

        String docType = sub != null ? sub : (detectedType != null ? detectedType : (cat != null ? cat : "UNKNOWN"));
        boolean isPassport = "PASSPORT".equalsIgnoreCase(cat) || "PASSPORT".equalsIgnoreCase(sub) || "PASSPORT".equalsIgnoreCase(detectedType);
        boolean hasMrzData = data.getMrzData() != null && !data.getMrzData().isBlank();

        if (isPassport) {
            // --- 1. Passport ICAO 9303 MRZ Checkdigits ----------------------
            Optional<Mrz.Parsed> mrz = Mrz.parseTd3(data.getMrzData());
            if (mrz.isPresent()) {
                Mrz.Parsed m = mrz.get();
                if (!m.documentNumberValid()) { mrzChecksumFailed = true; reasons.add("MRZ passport-number check digit FAILED"); }
                if (!m.dobValid())            { mrzChecksumFailed = true; reasons.add("MRZ date-of-birth check digit FAILED"); }
                if (!m.expiryValid())         { mrzChecksumFailed = true; reasons.add("MRZ expiry-date check digit FAILED"); }
                if (!m.finalCheckValid())     { mrzChecksumFailed = true; reasons.add("MRZ composite check digit FAILED"); }
                if (m.allChecksValid())       reasons.add("MRZ check digits: all valid");

                // Cross-zone consistency (MRZ vs visual zone)
                crossZoneMismatch |= mismatch("passport number", m.documentNumber(), data.getPassportNumber(), reasons);
                crossZoneMismatch |= mismatch("date of birth", str(m.dateOfBirth()), str(data.getDateOfBirth()), reasons);
                crossZoneMismatch |= mismatch("expiry date", str(m.expiryDate()), str(data.getExpiryDate()), reasons);
                crossZoneMismatch |= mismatch("surname", m.surname(), surnameOf(data.getName()), reasons);
            } else if (hasMrzData) {
                reasons.add("Passport MRZ present but unparseable or corrupted");
                mrzChecksumFailed = true;
            } else {
                reasons.add("Passport MRZ missing or unreadable");
                mrzChecksumFailed = true;
            }
        } else if (hasClassification) {
            // --- 2. Known Non-Passport Documents (National ID, Driving Licence, Aadhaar, PAN, Visa, etc.) ------
            reasons.add("Document classification active: " + docType);
            if (hasMrzData) {
                Optional<Mrz.Parsed> mrz = Mrz.parseTd3(data.getMrzData());
                if (mrz.isPresent()) {
                    Mrz.Parsed m = mrz.get();
                    if (!m.documentNumberValid()) { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (document number)"); }
                    if (!m.dobValid())            { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (date of birth)"); }
                    if (!m.expiryValid())         { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (expiry date)"); }
                    if (!m.finalCheckValid())     { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (composite)"); }
                    if (m.allChecksValid())       reasons.add("MRZ check digits: all valid");
                } else {
                    reasons.add("MRZ present on " + docType + " but unparseable or corrupted");
                    mrzChecksumFailed = true;
                }
            } else {
                reasons.add("MRZ check digits: NOT_APPLICABLE (" + docType + ")");
            }

            boolean qrDetected = ocr != null && Boolean.TRUE.equals(ocr.qrDetected());
            boolean qrDecoded = ocr != null && Boolean.TRUE.equals(ocr.qrDecoded());
            boolean qrSigVerified = ocr != null && Boolean.TRUE.equals(ocr.qrSignatureVerified());
            String qrMatchStatus = ocr != null && ocr.qrOcrMatchStatus() != null ? ocr.qrOcrMatchStatus() : "NOT_APPLICABLE";

            if (qrDetected) {
                reasons.add("National ID QR Code detected — Decoded: " + qrDecoded + " | Cryptographic Signature: " + (qrSigVerified ? "VERIFIED" : "UNVERIFIED (No PKI Cert Chain Root)"));
                if ("MISMATCH".equalsIgnoreCase(qrMatchStatus)) {
                    crossZoneMismatch = true;
                    reasons.add("CRITICAL SECURITY ALARM: National ID QR data vs Visual OCR field mismatch (" + (ocr.qrOcrDiscrepancies() != null ? ocr.qrOcrDiscrepancies() : "") + ")");
                } else if ("MATCH".equalsIgnoreCase(qrMatchStatus)) {
                    reasons.add("National ID QR ↔ Visual OCR field consistency: 100% MATCH");
                }
            } else {
                reasons.add("No QR Code detected on National ID document (Visual OCR audit performed)");
            }
        } else {
            // --- 3. Unclassified / Unknown Document Type -------------------
            reasons.add("Document type UNKNOWN / UNCLASSIFIED");
            if (hasMrzData) {
                Optional<Mrz.Parsed> mrz = Mrz.parseTd3(data.getMrzData());
                if (mrz.isPresent()) {
                    Mrz.Parsed m = mrz.get();
                    if (!m.documentNumberValid()) { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (document number)"); }
                    if (!m.dobValid())            { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (date of birth)"); }
                    if (!m.expiryValid())         { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (expiry date)"); }
                    if (!m.finalCheckValid())     { mrzChecksumFailed = true; reasons.add("MRZ check digit FAILED (composite)"); }
                    if (m.allChecksValid())       reasons.add("MRZ check digits: all valid");
                } else {
                    reasons.add("MRZ present on UNKNOWN document but unparseable or corrupted");
                    mrzChecksumFailed = true;
                }
            } else {
                reasons.add("Document type unclassified — MRZ absent, defaulting to Visual Zone inspection");
            }
        }

        // --- 3. Expiry -----------------------------------------------------
        if (data.getExpiryDate() != null && data.getExpiryDate().isBefore(LocalDate.now())) {
            expired = true;
            reasons.add("Document EXPIRED on " + data.getExpiryDate());
        }

        // --- 4. DOB plausibility ----------------------------------------
        if (data.getDateOfBirth() != null) {
            if (data.getDateOfBirth().isAfter(LocalDate.now())) {
                reasons.add("Date of birth is in the future — implausible");
                crossZoneMismatch = true;
            } else if (data.getDateOfBirth().isBefore(LocalDate.now().minusYears(120))) {
                reasons.add("Date of birth implies age > 120 — implausible");
                crossZoneMismatch = true;
            }
        }

        boolean failed = mrzChecksumFailed || expired || crossZoneMismatch;
        return new Outcome(failed, failed ? "FAIL" : "PASS", reasons,
                mrzChecksumFailed, expired, crossZoneMismatch);
    }

    private boolean mismatch(String field, String mrzValue, String visualValue, List<String> reasons) {
        if (mrzValue == null || visualValue == null) return false;
        String a = mrzValue.trim().toUpperCase().replace(" ", "");
        String b = visualValue.trim().toUpperCase().replace(" ", "");
        if (a.isEmpty() || b.isEmpty()) return false;
        if (!a.equals(b)) {
            reasons.add("Cross-zone mismatch on " + field + ": MRZ='" + mrzValue + "' vs visual='" + visualValue + "'");
            return true;
        }
        return false;
    }

    private static String str(LocalDate d) { return d == null ? null : d.toString(); }

    private static String surnameOf(String fullName) {
        if (fullName == null || fullName.isBlank()) return null;
        String[] parts = fullName.trim().split("\\s+");
        return parts[parts.length - 1];
    }
}
