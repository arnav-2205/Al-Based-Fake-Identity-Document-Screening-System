package gov.mha.screening;

import gov.mha.screening.ai.AiDtos;
import gov.mha.screening.extraction.ExtractedData;
import gov.mha.screening.validation.ValidationEngine;
import org.junit.jupiter.api.Test;

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
}
