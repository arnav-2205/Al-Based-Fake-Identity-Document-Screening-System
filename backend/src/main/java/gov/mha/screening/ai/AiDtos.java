package gov.mha.screening.ai;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/** Response shapes from the Python AI service. Loosely typed on purpose. */
public final class AiDtos {

    private AiDtos() {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record OcrResult(
            @JsonProperty("mrz") String mrz,
            @JsonProperty("fields") Map<String, String> fields,
            @JsonProperty("visualZone") Map<String, Object> visualZone,
            @JsonProperty("confidence") Double confidence,
            @JsonProperty("fieldConfidences") Map<String, Double> fieldConfidences,
            @JsonProperty("fieldStates") Map<String, String> fieldStates,
            @JsonProperty("mrzValid") Boolean mrzValid,
            @JsonProperty("mrzChecks") Map<String, Boolean> mrzChecks,
            @JsonProperty("notes") List<String> notes,
            @JsonProperty("detectedDocumentType") String detectedDocumentType,
            @JsonProperty("documentCategory") String documentCategory,
            @JsonProperty("documentSubtype") String documentSubtype,
            @JsonProperty("applicableFields") List<String> applicableFields,
            @JsonProperty("applicableChecks") List<String> applicableChecks,
            @JsonProperty("issuingCountry") String issuingCountry,
            @JsonProperty("qrDetected") Boolean qrDetected,
            @JsonProperty("qrDecoded") Boolean qrDecoded,
            @JsonProperty("qrSignatureVerified") Boolean qrSignatureVerified,
            @JsonProperty("qrSignatureStatus") String qrSignatureStatus,
            @JsonProperty("qrStatus") String qrStatus,
            @JsonProperty("qrData") Map<String, Object> qrData,
            @JsonProperty("qrOcrMatchStatus") String qrOcrMatchStatus,
            @JsonProperty("qrOcrDiscrepancies") List<String> qrOcrDiscrepancies,
            @JsonProperty("barcodeDetected") Boolean barcodeDetected,
            @JsonProperty("barcodeDecoded") Boolean barcodeDecoded,
            @JsonProperty("barcodeStatus") String barcodeStatus,
            @JsonProperty("barcodeType") String barcodeType,
            @JsonProperty("barcodeData") Object barcodeData,
            @JsonProperty("mrzStatus") String mrzStatus
    ) {
        @JsonCreator
        public OcrResult {
        }

        public OcrResult(
                String mrz,
                Map<String, String> fields,
                Map<String, Object> visualZone,
                Double confidence,
                Boolean mrzValid,
                Map<String, Boolean> mrzChecks,
                List<String> notes
        ) {
            this(
                    mrz,
                    fields,
                    visualZone,
                    confidence,
                    Map.of(),
                    Map.of(),
                    mrzValid,
                    mrzChecks,
                    notes,
                    null,
                    null,
                    null,
                    List.of(),
                    List.of(),
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    List.of(),
                    null,
                    null,
                    null,
                    null,
                    null,
                    null
            );
        }
    }

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
