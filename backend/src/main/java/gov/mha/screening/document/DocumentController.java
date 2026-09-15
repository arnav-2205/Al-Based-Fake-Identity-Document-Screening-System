package gov.mha.screening.document;

import gov.mha.screening.ai.AiClient;
import gov.mha.screening.ai.AiDtos;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService service;
    private final AiClient aiClient;

    @PostMapping(value = "/upload", consumes = "multipart/form-data")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR')")
    public Map<String, Object> upload(@RequestParam(value = "documentType", required = false) String documentType,
                                      @RequestParam(value = "file", required = false) MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw gov.mha.screening.common.ApiException.badRequest("Document file is required");
        }
        Document d = service.upload(documentType, file);
        return Map.of(
                "documentId", d.getId(),
                "documentType", d.getDocumentType(),
                "fileHash", d.getFileHash(),
                "fileReference", d.getFileReference());
    }

    @PostMapping(value = "/extract-ocr", consumes = "multipart/form-data")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR')")
    public AiDtos.OcrResult extractOcr(@RequestParam(value = "file", required = false) MultipartFile file) {
        if (file == null || file.isEmpty()) {
            return new AiDtos.OcrResult(
                    null, Map.of(), Map.of(), 0.0, Map.of(), Map.of(),
                    false, Map.of(), List.of("OCR extraction failure: Document file is required"),
                    "UNKNOWN", "NATIONAL_ID", "NATIONAL_ID_CARD", List.of(), List.of(),
                    "UNKNOWN", false, false, false, "NOT_AVAILABLE", "NOT_AVAILABLE",
                    null, "NOT_APPLICABLE", List.of(), false, false, "NOT_AVAILABLE",
                    "NONE", null, "NOT_AVAILABLE", "UNKNOWN", 0.0,
                    null, null, null, null);
        }
        try {
            return aiClient.extractOcr(file.getBytes());
        } catch (Exception e) {
            return new AiDtos.OcrResult(
                    null, Map.of(), Map.of(), 0.0, Map.of(), Map.of(),
                    false, Map.of(), List.of("OCR extraction failure: " + e.getMessage()),
                    "UNKNOWN", "NATIONAL_ID", "NATIONAL_ID_CARD", List.of(), List.of(),
                    "UNKNOWN", false, false, false, "NOT_AVAILABLE", "NOT_AVAILABLE",
                    null, "NOT_APPLICABLE", List.of(), false, false, "NOT_AVAILABLE",
                    "NONE", null, "NOT_AVAILABLE", "UNKNOWN", 0.0,
                    null, null, null, null);
        }
    }
}
