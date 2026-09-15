package gov.mha.screening;

import gov.mha.screening.ai.AiDtos;
import gov.mha.screening.extraction.ExtractedData;
import gov.mha.screening.validation.ValidationEngine;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ValidationEngineTest {

    private final ValidationEngine engine = new ValidationEngine();

    @Test
    void nationalIdWithoutMrzDoesNotFailMrzChecksum() {
        ExtractedData data = new ExtractedData();
        data.setVisualZone(Map.of(
                "documentCategory", "NATIONAL_ID",
                "documentSubtype", "NATIONAL_ID_CARD",
                "detectedDocumentType", "NATIONAL_ID_CARD"
        ));

        AiDtos.OcrResult ocr = new AiDtos.OcrResult(
                null,
                Map.of("issuingCountry", "INDIA"),
                data.getVisualZone(),
                0.95,
                true,
                Map.of(),
                List.of("Generic National ID Adapter active")
        );

        ValidationEngine.Outcome outcome = engine.validate(data, ocr);

        assertFalse(outcome.mrzChecksumFailed(), "National ID without MRZ must NOT set mrzChecksumFailed");
        assertFalse(outcome.failed(), "National ID without MRZ must pass deterministic validation when no other failure exists");
        assertEquals("PASS", outcome.status());
        assertEquals("NOT_APPLICABLE", outcome.vizMrzCrossValidation().status());
        assertTrue(outcome.reasons().stream().anyMatch(r -> r.contains("NOT_APPLICABLE")),
                "Reasons should state MRZ is NOT_APPLICABLE for National ID");
    }

    @Test
    void passportWithoutMrzTriggersMrzChecksumFailed() {
        ExtractedData data = new ExtractedData();
        data.setVisualZone(Map.of(
                "documentCategory", "PASSPORT",
                "documentSubtype", "PASSPORT",
                "detectedDocumentType", "PASSPORT"
        ));

        AiDtos.OcrResult ocr = new AiDtos.OcrResult(
                null,
                Map.of(),
                data.getVisualZone(),
                0.95,
                false,
                Map.of(),
                List.of()
        );

        ValidationEngine.Outcome outcome = engine.validate(data, ocr);

        assertTrue(outcome.mrzChecksumFailed(), "Passport without MRZ must trigger mrzChecksumFailed");
        assertTrue(outcome.failed(), "Passport without MRZ must fail validation");
        assertEquals("FAIL", outcome.status());
        assertEquals("INCONCLUSIVE", outcome.vizMrzCrossValidation().status());
    }

    @Test
    void passportWithCorruptedMrzTriggersMrzChecksumFailed() {
        ExtractedData data = new ExtractedData();
        String tamperedMrz =
                "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n" +
                "L898902C99UTO7408122F1204159ZE184226B<<<<<10";
        data.setMrzData(tamperedMrz);
        data.setVisualZone(Map.of(
                "documentCategory", "PASSPORT",
                "documentSubtype", "PASSPORT",
                "detectedDocumentType", "PASSPORT"
        ));

        AiDtos.OcrResult ocr = new AiDtos.OcrResult(
                tamperedMrz,
                Map.of(),
                data.getVisualZone(),
                0.95,
                false,
                Map.of("documentNumber", false),
                List.of()
        );

        ValidationEngine.Outcome outcome = engine.validate(data, ocr);

        assertTrue(outcome.mrzChecksumFailed(), "Passport with corrupted MRZ checkdigit must trigger mrzChecksumFailed");
        assertTrue(outcome.failed());
    }

    @Test
    void unclassifiedDocumentWithoutMrzDoesNotDefaultToNationalId() {
        ExtractedData data = new ExtractedData();
        data.setVisualZone(Map.of()); // No classification keys

        AiDtos.OcrResult ocr = new AiDtos.OcrResult(
                null,
                Map.of(),
                Map.of(),
                0.5,
                false,
                Map.of(),
                List.of()
        );

        ValidationEngine.Outcome outcome = engine.validate(data, ocr);

        assertFalse(outcome.mrzChecksumFailed(), "Unclassified document without MRZ must not set mrzChecksumFailed");
        assertTrue(outcome.reasons().stream().anyMatch(r -> r.contains("UNKNOWN / UNCLASSIFIED")),
                "Reasons should explicitly state UNKNOWN / UNCLASSIFIED document type");
    }

    @Test
    void unclassifiedDocumentWithCorruptedMrzTriggersMrzChecksumFailed() {
        ExtractedData data = new ExtractedData();
        data.setMrzData("CORRUPTED_MRZ_DATA_LINE");
        data.setVisualZone(Map.of());

        AiDtos.OcrResult ocr = new AiDtos.OcrResult(
                "CORRUPTED_MRZ_DATA_LINE",
                Map.of(),
                Map.of(),
                0.5,
                false,
                Map.of(),
                List.of()
        );

        ValidationEngine.Outcome outcome = engine.validate(data, ocr);

        assertTrue(outcome.mrzChecksumFailed(), "Unclassified document with corrupted MRZ payload must trigger mrzChecksumFailed");
        assertTrue(outcome.failed());
    }

    @Test
    void vizMrzCrossValidationDetectsDobMismatch() {
        ExtractedData data = new ExtractedData();
        String validMrz =
                "P<UTOTESTER<<ALEXANDER<<<<<<<<<<<<<<<<<<<<<<\n" +
                "T123456784UTO9001159M3512317<<<<<<<<<<<<<<00";
        data.setMrzData(validMrz);
        data.setName("ALEXANDER TESTER");
        data.setPassportNumber("T12345678");
        data.setNationality("UTO");
        data.setDateOfBirth(LocalDate.of(1991, 1, 15)); // Mismatched DOB (VIZ 1991 vs MRZ 1990)
        data.setExpiryDate(LocalDate.of(2035, 12, 31));
        data.setVisualZone(Map.of("documentCategory", "PASSPORT"));

        ValidationEngine.Outcome outcome = engine.validate(data, null);
        assertNotNull(outcome.vizMrzCrossValidation());
        assertEquals("MISMATCH", outcome.vizMrzCrossValidation().status());
        assertTrue(outcome.vizMrzCrossValidation().mismatches().stream().anyMatch(m -> "dateOfBirth".equals(m.field())));
    }

    @Test
    void vizMrzCrossValidationDetectsDocNumMismatch() {
        ExtractedData data = new ExtractedData();
        String validMrz =
                "P<UTOTESTER<<ALEXANDER<<<<<<<<<<<<<<<<<<<<<<\n" +
                "T123456784UTO9001159M3512317<<<<<<<<<<<<<<00";
        data.setMrzData(validMrz);
        data.setName("ALEXANDER TESTER");
        data.setPassportNumber("T12345679"); // Mismatched Doc Num
        data.setNationality("UTO");
        data.setDateOfBirth(LocalDate.of(1990, 1, 15));
        data.setExpiryDate(LocalDate.of(2035, 12, 31));
        data.setVisualZone(Map.of("documentCategory", "PASSPORT"));

        ValidationEngine.Outcome outcome = engine.validate(data, null);
        assertNotNull(outcome.vizMrzCrossValidation());
        assertEquals("MISMATCH", outcome.vizMrzCrossValidation().status());
        assertTrue(outcome.vizMrzCrossValidation().mismatches().stream().anyMatch(m -> "documentNumber".equals(m.field())));
    }

    @Test
    void vizMrzCrossValidationMissingVizFieldIsUnavailableNotMismatch() {
        ExtractedData data = new ExtractedData();
        String validMrz =
                "P<UTOTESTER<<ALEXANDER<<<<<<<<<<<<<<<<<<<<<<\n" +
                "T123456784UTO9001159M3512317<<<<<<<<<<<<<<00";
        data.setMrzData(validMrz);
        data.setName("ALEXANDER TESTER");
        data.setPassportNumber("T12345678");
        data.setDateOfBirth(null); // Missing VIZ DOB
        data.setNationality("UTO");
        data.setExpiryDate(LocalDate.of(2035, 12, 31));
        data.setVisualZone(Map.of("documentCategory", "PASSPORT"));

        ValidationEngine.Outcome outcome = engine.validate(data, null);
        assertNotNull(outcome.vizMrzCrossValidation());
        assertEquals("MATCH", outcome.vizMrzCrossValidation().status());
        assertFalse(outcome.vizMrzCrossValidation().matchedFields().contains("dateOfBirth"));
        assertEquals(0, outcome.vizMrzCrossValidation().mismatches().size());
    }

    @Test
    void expiryValidationFutureExpiryIsValid() {
        ExtractedData data = new ExtractedData();
        String validMrz =
                "P<UTOTESTER<<ALEXANDER<<<<<<<<<<<<<<<<<<<<<<\n" +
                "T123456784UTO9001159M3512317<<<<<<<<<<<<<<00";
        data.setMrzData(validMrz);
        data.setVisualZone(Map.of("documentCategory", "PASSPORT"));

        ValidationEngine.Outcome outcome = engine.validate(data, null);
        assertNotNull(outcome.expiryValidation());
        assertEquals("VALID", outcome.expiryValidation().status());
        assertEquals(LocalDate.of(2035, 12, 31), outcome.expiryValidation().expiryDate());
        assertEquals("MRZ", outcome.expiryValidation().source());
        assertFalse(outcome.expired());
    }

    @Test
    void expiryValidationPastExpiryIsExpired() {
        ExtractedData data = new ExtractedData();
        data.setExpiryDate(LocalDate.of(2024, 1, 15));
        data.setVisualZone(Map.of("documentCategory", "NATIONAL_ID", "documentSubtype", "NATIONAL_ID_CARD"));

        ValidationEngine.Outcome outcome = engine.validate(data, null);
        assertNotNull(outcome.expiryValidation());
        assertEquals("EXPIRED", outcome.expiryValidation().status());
        assertEquals(LocalDate.of(2024, 1, 15), outcome.expiryValidation().expiryDate());
        assertEquals("VIZ", outcome.expiryValidation().source());
        assertTrue(outcome.expired());
    }

    @Test
    void expiryValidationAadhaarIsNotApplicable() {
        ExtractedData data = new ExtractedData();
        data.setVisualZone(Map.of("documentCategory", "NATIONAL_ID", "documentSubtype", "AADHAAR"));

        ValidationEngine.Outcome outcome = engine.validate(data, null);
        assertNotNull(outcome.expiryValidation());
        assertEquals("NOT_APPLICABLE", outcome.expiryValidation().status());
        assertNull(outcome.expiryValidation().expiryDate());
        assertFalse(outcome.expired());
    }

    @Test
    void expiryValidationUnknownExpiryIsUnknownNotExpired() {
        ExtractedData data = new ExtractedData();
        data.setVisualZone(Map.of("documentCategory", "DRIVING_LICENCE", "documentSubtype", "DRIVING_LICENCE"));

        ValidationEngine.Outcome outcome = engine.validate(data, null);
        assertNotNull(outcome.expiryValidation());
        assertEquals("UNKNOWN", outcome.expiryValidation().status());
        assertNull(outcome.expiryValidation().expiryDate());
        assertFalse(outcome.expired());
    }

    @Test
    void riskEngineP1_5_PhotoReplacement_TriggersPlus15() {
        gov.mha.screening.config.AppProperties props = new gov.mha.screening.config.AppProperties(
                null, null, null, null,
                new gov.mha.screening.config.AppProperties.Risk(
                        new gov.mha.screening.config.AppProperties.Risk.Weights(25, 20, 20, 20, 10, 5),
                        new gov.mha.screening.config.AppProperties.Risk.Thresholds(0.50, 0.55)
                ),
                null
        );
        gov.mha.screening.risk.RiskEngine re = new gov.mha.screening.risk.RiskEngine(props);
        gov.mha.screening.risk.RiskEngine.Input in = new gov.mha.screening.risk.RiskEngine.Input(
                0.0, 0.8, false, false, false, false, true, true, false, false, null
        );
        gov.mha.screening.risk.RiskEngine.RiskAssessment ra = re.assessRisk(in);
        assertEquals(15.0, ra.score());
        assertTrue(ra.triggeredComponents().stream().anyMatch(c -> "PHOTO_REPLACEMENT".equals(c.code())));
    }

    @Test
    void riskEngineP1_5_TextManipulation_TriggersPlus15() {
        gov.mha.screening.config.AppProperties props = new gov.mha.screening.config.AppProperties(
                null, null, null, null,
                new gov.mha.screening.config.AppProperties.Risk(
                        new gov.mha.screening.config.AppProperties.Risk.Weights(25, 20, 20, 20, 10, 5),
                        new gov.mha.screening.config.AppProperties.Risk.Thresholds(0.50, 0.55)
                ),
                null
        );
        gov.mha.screening.risk.RiskEngine re = new gov.mha.screening.risk.RiskEngine(props);
        gov.mha.screening.risk.RiskEngine.Input in = new gov.mha.screening.risk.RiskEngine.Input(
                0.0, 0.8, false, false, false, false, true, false, true, false, null
        );
        gov.mha.screening.risk.RiskEngine.RiskAssessment ra = re.assessRisk(in);
        assertEquals(15.0, ra.score());
        assertTrue(ra.triggeredComponents().stream().anyMatch(c -> "TEXT_MANIPULATION".equals(c.code())));
    }

    @Test
    void riskEngineP1_5_VizMrzMismatch_TriggersPlus15() {
        gov.mha.screening.config.AppProperties props = new gov.mha.screening.config.AppProperties(
                null, null, null, null,
                new gov.mha.screening.config.AppProperties.Risk(
                        new gov.mha.screening.config.AppProperties.Risk.Weights(25, 20, 20, 20, 10, 5),
                        new gov.mha.screening.config.AppProperties.Risk.Thresholds(0.50, 0.55)
                ),
                null
        );
        gov.mha.screening.risk.RiskEngine re = new gov.mha.screening.risk.RiskEngine(props);
        gov.mha.screening.risk.RiskEngine.Input in = new gov.mha.screening.risk.RiskEngine.Input(
                0.0, 0.8, false, false, false, false, true, false, false, true, null
        );
        gov.mha.screening.risk.RiskEngine.RiskAssessment ra = re.assessRisk(in);
        assertEquals(15.0, ra.score());
        assertTrue(ra.triggeredComponents().stream().anyMatch(c -> "VIZ_MRZ_MISMATCH".equals(c.code())));
    }

    @Test
    void riskEngineP1_5_ExpiredDocument_TriggersPlus15() {
        gov.mha.screening.config.AppProperties props = new gov.mha.screening.config.AppProperties(
                null, null, null, null,
                new gov.mha.screening.config.AppProperties.Risk(
                        new gov.mha.screening.config.AppProperties.Risk.Weights(25, 20, 20, 20, 10, 5),
                        new gov.mha.screening.config.AppProperties.Risk.Thresholds(0.50, 0.55)
                ),
                null
        );
        gov.mha.screening.risk.RiskEngine re = new gov.mha.screening.risk.RiskEngine(props);
        gov.mha.screening.validation.ExpiryValidation exp = new gov.mha.screening.validation.ExpiryValidation(
                "EXPIRED", LocalDate.of(2020, 1, 1), -1500L, "MRZ"
        );
        gov.mha.screening.risk.RiskEngine.Input in = new gov.mha.screening.risk.RiskEngine.Input(
                0.0, 0.8, false, false, false, false, true, false, false, false, exp
        );
        gov.mha.screening.risk.RiskEngine.RiskAssessment ra = re.assessRisk(in);
        assertEquals(15.0, ra.score());
        assertEquals("MANUAL_REVIEW", ra.decision());
        assertTrue(ra.triggeredComponents().stream().anyMatch(c -> "EXPIRED_DOCUMENT".equals(c.code())));
    }

    @Test
    void riskEngineP1_5_ScoreConsistency_SumEqualsScore() {
        gov.mha.screening.config.AppProperties props = new gov.mha.screening.config.AppProperties(
                null, null, null, null,
                new gov.mha.screening.config.AppProperties.Risk(
                        new gov.mha.screening.config.AppProperties.Risk.Weights(25, 20, 20, 20, 10, 5),
                        new gov.mha.screening.config.AppProperties.Risk.Thresholds(0.50, 0.55)
                ),
                null
        );
        gov.mha.screening.risk.RiskEngine re = new gov.mha.screening.risk.RiskEngine(props);
        gov.mha.screening.risk.RiskEngine.Input in = new gov.mha.screening.risk.RiskEngine.Input(
                0.8, 0.2, true, true, false, false, true, true, true, true, null
        );
        gov.mha.screening.risk.RiskEngine.RiskAssessment ra = re.assessRisk(in);
        double sum = ra.components().stream().mapToDouble(c -> c.points()).sum();
        assertEquals(Math.min(100.0, sum), ra.score(), 0.01);
        assertEquals("REJECT", ra.decision());
        assertTrue(ra.securityOverrideTriggered());
    }

    @Test
    void riskEngineP1_6_StampForgery_TriggersPlus15() {
        gov.mha.screening.config.AppProperties props = new gov.mha.screening.config.AppProperties(
                null, null, null, null,
                new gov.mha.screening.config.AppProperties.Risk(
                        new gov.mha.screening.config.AppProperties.Risk.Weights(25, 20, 20, 20, 10, 5),
                        new gov.mha.screening.config.AppProperties.Risk.Thresholds(0.50, 0.55)
                ),
                null
        );
        gov.mha.screening.risk.RiskEngine re = new gov.mha.screening.risk.RiskEngine(props);
        gov.mha.screening.risk.RiskEngine.Input in = new gov.mha.screening.risk.RiskEngine.Input(
                0.0, 0.8, false, false, false, false, true, false, false, false, null, true
        );
        gov.mha.screening.risk.RiskEngine.RiskAssessment ra = re.assessRisk(in);
        assertEquals(15.0, ra.score());
        assertTrue(ra.triggeredComponents().stream().anyMatch(c -> "STAMP_FORGERY".equals(c.code())));
    }

    @Test
    void riskEngineP1_7_MetadataAnomaly_TriggersPlus5() {
        gov.mha.screening.config.AppProperties props = new gov.mha.screening.config.AppProperties(
                null, null, null, null,
                new gov.mha.screening.config.AppProperties.Risk(
                        new gov.mha.screening.config.AppProperties.Risk.Weights(25, 20, 20, 20, 10, 5),
                        new gov.mha.screening.config.AppProperties.Risk.Thresholds(0.50, 0.55)
                ),
                null
        );
        gov.mha.screening.risk.RiskEngine re = new gov.mha.screening.risk.RiskEngine(props);
        gov.mha.screening.risk.RiskEngine.Input in = new gov.mha.screening.risk.RiskEngine.Input(
                0.0, 0.8, false, false, false, false, true, false, false, false, null, false, true
        );
        gov.mha.screening.risk.RiskEngine.RiskAssessment ra = re.assessRisk(in);
        assertEquals(5.0, ra.score());
        assertTrue(ra.triggeredComponents().stream().anyMatch(c -> "METADATA_ANOMALY".equals(c.code())));
    }
}
