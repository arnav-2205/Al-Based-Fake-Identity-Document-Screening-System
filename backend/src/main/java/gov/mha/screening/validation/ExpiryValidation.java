package gov.mha.screening.validation;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

/**
 * Structured result of document expiry validation.
 */
public record ExpiryValidation(
        String status,              // VALID | EXPIRED | UNKNOWN | NOT_APPLICABLE
        LocalDate expiryDate,
        Long daysRemaining,         // positive for future, negative for past, null if unknown/not applicable
        String source               // MRZ | VIZ | null
) {
    public static ExpiryValidation of(LocalDate date, String source) {
        if (date == null) {
            return unknown("Expiry date field not present or unextracted");
        }
        LocalDate now = LocalDate.now();
        long days = ChronoUnit.DAYS.between(now, date);
        if (date.isBefore(now)) {
            return new ExpiryValidation("EXPIRED", date, days, source);
        }
        return new ExpiryValidation("VALID", date, days, source);
    }

    public static ExpiryValidation unknown(String reason) {
        return new ExpiryValidation("UNKNOWN", null, null, null);
    }

    public static ExpiryValidation notApplicable() {
        return new ExpiryValidation("NOT_APPLICABLE", null, null, null);
    }
}
