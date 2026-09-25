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
            boolean crossZoneMismatch,
            VizMrzCrossValidation vizMrzCrossValidation,
            ExpiryValidation expiryValidation
    ) {}

    public Outcome validate(ExtractedData data, AiDtos.OcrResult ocr) {
        return validate(data, ocr, null);
    }

    public Outcome validate(ExtractedData data, AiDtos.OcrResult ocr, String selectedType) {
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

        String effectiveType = selectedType != null && !selectedType.isBlank() && !"UNKNOWN".equalsIgnoreCase(selectedType)
                ? selectedType
                : (sub != null ? sub : (detectedType != null ? detectedType : (cat != null ? cat : "UNKNOWN")));

        boolean isExplicitNonPassport = "VISA".equalsIgnoreCase(selectedType)
                || "DRIVING_LICENCE".equalsIgnoreCase(selectedType)
                || "NATIONAL_ID".equalsIgnoreCase(selectedType)
                || "OTHER_GOVT_DOC".equalsIgnoreCase(selectedType)
                || "VISA".equalsIgnoreCase(effectiveType)
                || "DRIVING_LICENCE".equalsIgnoreCase(effectiveType)
                || "AADHAAR".equalsIgnoreCase(effectiveType)
                || "PAN".equalsIgnoreCase(effectiveType);

        boolean isPassport = !isExplicitNonPassport && ("PASSPORT".equalsIgnoreCase(effectiveType)
                || "PASSPORT".equalsIgnoreCase(cat)
                || "PASSPORT".equalsIgnoreCase(sub)
                || "PASSPORT".equalsIgnoreCase(detectedType));

        boolean hasClassification = isPassport || isExplicitNonPassport
                || (cat != null && !"UNKNOWN".equalsIgnoreCase(cat))
                || (sub != null && !"UNKNOWN".equalsIgnoreCase(sub))
                || (detectedType != null && !"UNKNOWN".equalsIgnoreCase(detectedType));

        String docType = effectiveType;
        boolean hasMrzData = data.getMrzData() != null && !data.getMrzData().isBlank();

        Optional<Mrz.Parsed> parsedMrz = hasMrzData ? Mrz.parseTd3(data.getMrzData()) : Optional.empty();

        if (isPassport) {
            // --- 1. Passport ICAO 9303 MRZ Checkdigits ----------------------
            if (parsedMrz.isPresent()) {
                Mrz.Parsed m = parsedMrz.get();
                if (!m.documentNumberValid()) { mrzChecksumFailed = true; reasons.add("MRZ passport-number check digit FAILED"); }
                if (!m.dobValid())            { mrzChecksumFailed = true; reasons.add("MRZ date-of-birth check digit FAILED"); }
                if (!m.expiryValid())         { mrzChecksumFailed = true; reasons.add("MRZ expiry-date check digit FAILED"); }
                if (!m.finalCheckValid())     { mrzChecksumFailed = true; reasons.add("MRZ composite check digit FAILED"); }
                if (m.allChecksValid())       reasons.add("MRZ check digits: all valid");
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
                if (parsedMrz.isPresent()) {
                    Mrz.Parsed m = parsedMrz.get();
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
                if (parsedMrz.isPresent()) {
                    Mrz.Parsed m = parsedMrz.get();
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

        // --- Perform VIZ ↔ MRZ Cross-Validation ---
        VizMrzCrossValidation vizMrz = performVizMrzCrossValidation(data, parsedMrz, docType, isPassport, hasMrzData);
        if ("MISMATCH".equals(vizMrz.status())) {
            crossZoneMismatch = true;
        }

        // --- Perform Document Expiry Validation ---
        ExpiryValidation expiryValidation = performExpiryValidation(data, parsedMrz, docType, isPassport, hasMrzData);
        if ("EXPIRED".equals(expiryValidation.status())) {
            expired = true;
            reasons.add("Document EXPIRED on " + expiryValidation.expiryDate() + " (" + Math.abs(expiryValidation.daysRemaining()) + " days ago)");
        } else if ("VALID".equals(expiryValidation.status())) {
            reasons.add("Document Expiry: VALID until " + expiryValidation.expiryDate() + " (" + expiryValidation.daysRemaining() + " days remaining)");
        } else if ("NOT_APPLICABLE".equals(expiryValidation.status())) {
            reasons.add("Document Expiry: NOT_APPLICABLE (" + docType + ")");
        } else {
            reasons.add("Document Expiry: UNKNOWN (unable to reliably determine expiry date)");
        }

        // --- DOB plausibility ----------------------------------------
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
                mrzChecksumFailed, expired, crossZoneMismatch, vizMrz, expiryValidation);
    }

    public ExpiryValidation performExpiryValidation(
            ExtractedData data,
            Optional<Mrz.Parsed> mrzOpt,
            String docType,
            boolean isPassport,
            boolean hasMrzData
    ) {
        String upperDocType = docType != null ? docType.toUpperCase() : "";
        if (upperDocType.contains("AADHAAR") || upperDocType.contains("PAN")
                || upperDocType.contains("VOTER") || upperDocType.contains("TAX_ID")
                || upperDocType.contains("SOCIAL_SECURITY")) {
            return ExpiryValidation.notApplicable();
        }

        // Priority 1: MRZ Expiry date
        if (mrzOpt.isPresent() && mrzOpt.get().expiryDate() != null) {
            return ExpiryValidation.of(mrzOpt.get().expiryDate(), "MRZ");
        }

        // Priority 2: VIZ Expiry date
        if (data.getExpiryDate() != null) {
            return ExpiryValidation.of(data.getExpiryDate(), "VIZ");
        }

        return ExpiryValidation.unknown("Expiry date could not be reliably determined");
    }

    public VizMrzCrossValidation performVizMrzCrossValidation(
            ExtractedData data,
            Optional<Mrz.Parsed> mrzOpt,
            String docType,
            boolean isPassport,
            boolean hasMrzData
    ) {
        if (!hasMrzData || mrzOpt.isEmpty()) {
            if (isPassport) {
                return VizMrzCrossValidation.inconclusive("Passport MRZ missing or unparseable — VIZ ↔ MRZ comparison unavailable");
            }
            return VizMrzCrossValidation.notApplicable("Document category (" + docType + ") has no MRZ — cross-validation NOT_APPLICABLE");
        }

        Mrz.Parsed mrz = mrzOpt.get();
        List<String> matchedFields = new ArrayList<>();
        List<VizMrzCrossValidation.FieldMismatch> mismatches = new ArrayList<>();
        List<String> reasons = new ArrayList<>();

        // 1. Name comparison
        String vizName = data.getName();
        String mrzSurname = mrz.surname();
        String mrzGiven = mrz.givenNames();
        String mrzFull = (mrzSurname != null ? mrzSurname : "") + (mrzGiven != null && !mrzGiven.isBlank() ? " " + mrzGiven : "");
        mrzFull = mrzFull.trim();

        if (vizName != null && !vizName.isBlank() && !mrzFull.isBlank()) {
            String normViz = vizName.toUpperCase().replaceAll("[^A-Z0-9 ]", "").replaceAll("\\s+", " ").trim();
            String normMrz = mrzFull.toUpperCase().replaceAll("[^A-Z0-9 ]", "").replaceAll("\\s+", " ").trim();
            String normVizSurname = surnameOf(vizName);
            String normMrzSurname = mrzSurname != null ? mrzSurname.toUpperCase().replaceAll("[^A-Z0-9]", "") : null;

            boolean nameMatches = normViz.equals(normMrz)
                    || (normVizSurname != null && normMrzSurname != null && !normVizSurname.isBlank() && normVizSurname.replaceAll("[^A-Z0-9]", "").equals(normMrzSurname));

            if (nameMatches) {
                matchedFields.add("name");
            } else {
                mismatches.add(new VizMrzCrossValidation.FieldMismatch("name", vizName, mrzFull));
                reasons.add("VIZ name '" + vizName + "' does not match MRZ name '" + mrzFull + "'");
            }
        }

        // 2. Date of Birth comparison
        LocalDate vizDob = data.getDateOfBirth();
        LocalDate mrzDob = mrz.dateOfBirth();
        if (vizDob != null && mrzDob != null) {
            if (vizDob.equals(mrzDob)) {
                matchedFields.add("dateOfBirth");
            } else {
                mismatches.add(new VizMrzCrossValidation.FieldMismatch("dateOfBirth", vizDob.toString(), mrzDob.toString()));
                reasons.add("VIZ date of birth '" + vizDob + "' does not match MRZ date of birth '" + mrzDob + "'");
            }
        }

        // 3. Document / Passport Number comparison
        String vizDocNum = data.getPassportNumber();
        if ((vizDocNum == null || vizDocNum.isBlank()) && data.getVisualZone() != null && data.getVisualZone().get("documentNumber") != null) {
            vizDocNum = String.valueOf(data.getVisualZone().get("documentNumber"));
        }
        String mrzDocNum = mrz.documentNumber();

        if (vizDocNum != null && !vizDocNum.isBlank() && mrzDocNum != null && !mrzDocNum.isBlank()) {
            String normVizDoc = vizDocNum.toUpperCase().replaceAll("[^A-Z0-9]", "");
            String normMrzDoc = mrzDocNum.toUpperCase().replaceAll("[^A-Z0-9]", "");

            if (normVizDoc.equals(normMrzDoc)) {
                matchedFields.add("documentNumber");
            } else {
                mismatches.add(new VizMrzCrossValidation.FieldMismatch("documentNumber", vizDocNum, mrzDocNum));
                reasons.add("VIZ document number '" + vizDocNum + "' does not match MRZ document number '" + mrzDocNum + "'");
            }
        }

        // 4. Nationality comparison
        String vizNat = data.getNationality();
        String mrzNat = mrz.nationality();

        if (vizNat != null && !vizNat.isBlank() && mrzNat != null && !mrzNat.isBlank()) {
            String normVizNat = vizNat.toUpperCase().trim();
            String normMrzNat = mrzNat.toUpperCase().trim();

            boolean natMatch = normVizNat.equals(normMrzNat)
                    || normVizNat.startsWith(normMrzNat)
                    || normMrzNat.startsWith(normVizNat);

            if (natMatch) {
                matchedFields.add("nationality");
            } else {
                mismatches.add(new VizMrzCrossValidation.FieldMismatch("nationality", vizNat, mrzNat));
                reasons.add("VIZ nationality '" + vizNat + "' does not match MRZ nationality '" + mrzNat + "'");
            }
        }

        // 5. Expiry Date comparison
        LocalDate vizExp = data.getExpiryDate();
        LocalDate mrzExp = mrz.expiryDate();
        if (vizExp != null && mrzExp != null) {
            if (vizExp.equals(mrzExp)) {
                matchedFields.add("expiryDate");
            } else {
                mismatches.add(new VizMrzCrossValidation.FieldMismatch("expiryDate", vizExp.toString(), mrzExp.toString()));
                reasons.add("VIZ expiry date '" + vizExp + "' does not match MRZ expiry date '" + mrzExp + "'");
            }
        }

        String status;
        if (!mismatches.isEmpty()) {
            status = "MISMATCH";
        } else if (!matchedFields.isEmpty()) {
            status = "MATCH";
        } else {
            status = "INCONCLUSIVE";
            reasons.add("VIZ ↔ MRZ cross-validation: INCONCLUSIVE (No overlapping fields available for comparison)");
        }

        return new VizMrzCrossValidation(status, matchedFields, mismatches, reasons);
    }

    private static String surnameOf(String fullName) {
        if (fullName == null || fullName.isBlank()) return null;
        String[] parts = fullName.trim().split("\\s+");
        return parts[parts.length - 1];
    }
}
