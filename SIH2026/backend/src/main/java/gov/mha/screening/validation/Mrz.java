package gov.mha.screening.validation;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Optional;

/**
 * ICAO 9303 TD3 (passport) MRZ parser + check-digit validation.
 * Deterministic, explainable — this is the most reliable fraud signal
 * for passport-number manipulation (Spec Part 1, case #5).
 */
public final class Mrz {

    private static final String WEIGHTS = "731";

    private Mrz() {}

    public record Parsed(
            String documentType,
            String issuingCountry,
            String surname,
            String givenNames,
            String documentNumber,
            String nationality,
            LocalDate dateOfBirth,
            String sex,
            LocalDate expiryDate,
            boolean documentNumberValid,
            boolean dobValid,
            boolean expiryValid,
            boolean finalCheckValid,
            boolean allChecksValid
    ) {}

    public static int charValue(char c) {
        if (c == '<') return 0;
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'A' && c <= 'Z') return c - 'A' + 10;
        return -1; // invalid
    }

    public static int checkDigit(String field) {
        int sum = 0;
        for (int i = 0; i < field.length(); i++) {
            int v = charValue(field.charAt(i));
            if (v < 0) return -1;
            sum += v * (WEIGHTS.charAt(i % 3) - '0');
        }
        return sum % 10;
    }

    public static boolean verify(String field, char providedCheck) {
        int computed = checkDigit(field);
        int provided = (providedCheck == '<') ? 0 : Character.digit(providedCheck, 10);
        return computed >= 0 && computed == provided;
    }

    /** Parse a 2-line, 44-char TD3 MRZ. Returns empty if the shape is wrong. */
    public static Optional<Parsed> parseTd3(String raw) {
        if (raw == null) return Optional.empty();
        String[] lines = raw.trim().replace(" ", "").split("\\R");
        if (lines.length < 2) return Optional.empty();
        String l1 = pad(lines[0]);
        String l2 = pad(lines[1]);
        if (l1.length() < 44 || l2.length() < 44) return Optional.empty();

        String documentType = l1.substring(0, 2).replace("<", "");
        String issuingCountry = l1.substring(2, 5).replace("<", "");
        String names = l1.substring(5, 44);
        String surname;
        String given;
        int sep = names.indexOf("<<");
        if (sep >= 0) {
            surname = names.substring(0, sep).replace("<", " ").trim();
            given = names.substring(sep + 2).replace("<", " ").trim();
        } else {
            surname = names.replace("<", " ").trim();
            given = "";
        }

        String docNum = l2.substring(0, 9);
        char docNumCheck = l2.charAt(9);
        String nationality = l2.substring(10, 13).replace("<", "");
        String dob = l2.substring(13, 19);
        char dobCheck = l2.charAt(19);
        String sex = String.valueOf(l2.charAt(20));
        String expiry = l2.substring(21, 27);
        char expiryCheck = l2.charAt(27);
        String optional = l2.substring(28, 42);
        char optionalCheck = l2.charAt(42);
        char finalCheck = l2.charAt(43);

        boolean docNumValid = verify(docNum, docNumCheck);
        boolean dobValid = verify(dob, dobCheck);
        boolean expiryValid = verify(expiry, expiryCheck);

        String composite = docNum + docNumCheck + dob + dobCheck + expiry + expiryCheck + optional + optionalCheck;
        boolean finalValid = verify(composite, finalCheck);

        return Optional.of(new Parsed(
                documentType, issuingCountry, surname, given,
                docNum.replace("<", ""), nationality,
                parseYymmdd(dob, true), sex, parseYymmdd(expiry, false),
                docNumValid, dobValid, expiryValid, finalValid,
                docNumValid && dobValid && expiryValid && finalValid));
    }

    private static String pad(String s) {
        StringBuilder sb = new StringBuilder(s);
        while (sb.length() < 44) sb.append('<');
        return sb.toString();
    }

    private static LocalDate parseYymmdd(String s, boolean isDob) {
        try {
            int yy = Integer.parseInt(s.substring(0, 2));
            int mm = Integer.parseInt(s.substring(2, 4));
            int dd = Integer.parseInt(s.substring(4, 6));
            int nowYy = LocalDate.now().getYear() % 100;
            int century = isDob ? (yy > nowYy ? 1900 : 2000) : (yy < 50 ? 2000 : 1900) + 0;
            if (!isDob) century = 2000; // expiry always assumed 21st century for demo
            return LocalDate.of(century + yy, mm, dd);
        } catch (Exception e) {
            return null;
        }
    }

    @SuppressWarnings("unused")
    private static final DateTimeFormatter YYMMDD = DateTimeFormatter.ofPattern("yyMMdd");
}
