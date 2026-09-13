package gov.mha.screening.ai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;
import java.util.Map;

/** Response shapes from the Python AI service. Loosely typed on purpose. */
public final class AiDtos {

    private AiDtos() {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record OcrResult(
            String mrz,
            Map<String, String> fields,
            Map<String, Object> visualZone,
            Double confidence,
            Map<String, Double> fieldConfidences,
            Map<String, String> fieldStates,
            Boolean mrzValid,
            Map<String, Boolean> mrzChecks,
            List<String> notes,
            String detectedDocumentType,
            String issuingCountry,
            Boolean qrDetected,
            Boolean qrDecoded,
            Boolean qrSignatureVerified,
            String qrSignatureStatus,
            String qrStatus,
            Map<String, Object> qrData,
            String qrOcrMatchStatus,
            List<String> qrOcrDiscrepancies,
            Boolean barcodeDetected,
            Boolean barcodeDecoded,
            String barcodeStatus,
            String barcodeType,
            Object barcodeData,
            String mrzStatus
    ) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record TamperResult(
            Double tamperingScore,
            Double photoTampering,
            Double textTampering,
            Double stampTampering,
            String elaHeatmapBase64,
            Map<String, Object> exif,
            List<String> notes
    ) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record FaceResult(
            Double faceMatchScore,
            String faceMatchStatus,
            String livenessStatus,
            List<Double> embedding,
            List<String> notes
    ) {}

    /** Aggregate returned by AiClient.analyzeAll(). */
    public record AiBundle(OcrResult ocr, TamperResult tamper, FaceResult face) {}
}
