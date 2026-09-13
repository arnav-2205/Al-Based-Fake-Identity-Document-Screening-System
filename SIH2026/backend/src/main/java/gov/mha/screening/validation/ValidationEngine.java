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

        // --- 1. MRZ check digits (ICAO 9303) --------------------------------
        Optional<Mrz.Parsed> mrz = Mrz.parseTd3(data.getMrzData());
        if (mrz.isPresent()) {
            Mrz.Parsed m = mrz.get();
            if (!m.documentNumberValid()) { mrzChecksumFailed = true; reasons.add("MRZ passport-number check digit FAILED"); }
            if (!m.dobValid())            { mrzChecksumFailed = true; reasons.add("MRZ date-of-birth check digit FAILED"); }
            if (!m.expiryValid())         { mrzChecksumFailed = true; reasons.add("MRZ expiry-date check digit FAILED"); }
            if (!m.finalCheckValid())     { mrzChecksumFailed = true; reasons.add("MRZ composite check digit FAILED"); }
            if (m.allChecksValid())       reasons.add("MRZ check digits: all valid");

            // --- 2. Cross-zone consistency (MRZ vs visual zone) -------------
            crossZoneMismatch |= mismatch("passport number", m.documentNumber(), data.getPassportNumber(), reasons);
            crossZoneMismatch |= mismatch("date of birth", str(m.dateOfBirth()), str(data.getDateOfBirth()), reasons);
            crossZoneMismatch |= mismatch("expiry date", str(m.expiryDate()), str(data.getExpiryDate()), reasons);
            crossZoneMismatch |= mismatch("surname", m.surname(), surnameOf(data.getName()), reasons);
        } else if (data.getMrzData() != null && !data.getMrzData().isBlank()) {
            reasons.add("MRZ present but could not be parsed as ICAO TD3");
        } else {
            reasons.add("No MRZ found on document");
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
