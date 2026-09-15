package gov.mha.screening.validation;

import java.util.List;

/**
 * Structured result of VIZ vs MRZ field cross-validation.
 */
public record VizMrzCrossValidation(
        String status,                  // MATCH | MISMATCH | PARTIAL | NOT_APPLICABLE | INCONCLUSIVE
        List<String> matchedFields,
        List<FieldMismatch> mismatches,
        List<String> reasons
) {
    public record FieldMismatch(
            String field,
            String vizValue,
            String mrzValue
    ) {}

    public static VizMrzCrossValidation notApplicable(String reason) {
        return new VizMrzCrossValidation(
                "NOT_APPLICABLE",
                List.of(),
                List.of(),
                List.of(reason != null ? reason : "VIZ ↔ MRZ cross-validation: NOT_APPLICABLE (Document has no MRZ)")
        );
    }

    public static VizMrzCrossValidation inconclusive(String reason) {
        return new VizMrzCrossValidation(
                "INCONCLUSIVE",
                List.of(),
                List.of(),
                List.of(reason != null ? reason : "VIZ ↔ MRZ cross-validation: INCONCLUSIVE (Insufficient data for comparison)")
        );
    }
}
