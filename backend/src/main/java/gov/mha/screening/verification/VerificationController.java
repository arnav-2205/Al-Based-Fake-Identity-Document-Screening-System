package gov.mha.screening.verification;

import gov.mha.screening.audit.AuditLog;
import gov.mha.screening.audit.AuditService;
import gov.mha.screening.security.CurrentUser;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/verification")
@RequiredArgsConstructor
public class VerificationController {

    private final VerificationService service;
    private final AuditService auditService;
    private final CurrentUser currentUser;

    private final com.fasterxml.jackson.databind.ObjectMapper objectMapper;

    @PostMapping("/start")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR')")
    public VerificationDtos.VerificationView start(@RequestParam(value = "documentId", required = false) Long documentId,
                                                  @RequestParam(value = "liveFace", required = false) MultipartFile liveFace,
                                                  HttpServletRequest request) throws IOException {
        Long docId = documentId;
        if (docId == null) {
            String param = request.getParameter("documentId");
            if (param != null && !param.isBlank()) {
                try {
                    docId = Long.parseLong(param.trim());
                } catch (NumberFormatException ignored) {}
            }
        }
        if (docId == null && request.getContentType() != null && request.getContentType().toLowerCase().contains("application/json")) {
            try {
                var map = objectMapper.readValue(request.getInputStream(), Map.class);
                if (map != null && map.get("documentId") != null) {
                    docId = Long.parseLong(map.get("documentId").toString());
                }
            } catch (Exception ignored) {}
        }
        if (docId == null) {
            throw gov.mha.screening.common.ApiException.badRequest("Missing required documentId parameter");
        }
        byte[] live = (liveFace != null && !liveFace.isEmpty()) ? liveFace.getBytes() : null;
        return service.start(docId, live, request.getRemoteAddr());
    }

    @GetMapping
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR','AUDITOR')")
    public List<VerificationDtos.VerificationView> listAll() {
        return service.listAll();
    }

    @GetMapping("/stats")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR','AUDITOR')")
    public Map<String, Object> stats() {
        return service.getStats();
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR','AUDITOR')")
    public VerificationDtos.VerificationView get(@PathVariable Long id) {
        return service.get(id);
    }

    @GetMapping("/{id}/heatmap")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR','AUDITOR')")
    public Map<String, String> heatmap(@PathVariable Long id) {
        return Map.of("elaHeatmapBase64", String.valueOf(service.heatmap(id)));
    }

    @GetMapping("/{id}/audit-trail")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR','AUDITOR')")
    public List<AuditLog> auditTrail(@PathVariable Long id) {
        return auditService.trail(id);
    }

    @GetMapping("/{id}/integrity-check")
    @PreAuthorize("hasAnyRole('ADMIN','INVESTIGATOR','AUDITOR')")
    public Map<String, Object> integrity(@PathVariable Long id) {
        return service.integrityCheck(id);
    }

    @PostMapping("/{id}/decision")
    @PreAuthorize("hasAnyRole('OFFICER','ADMIN','INVESTIGATOR')")
    public Map<String, Object> decision(@PathVariable Long id,
                                        @RequestBody VerificationDtos.DecisionRequest req,
                                        HttpServletRequest request) {
        auditService.record(id, currentUser.get().getId(),
                "OFFICER_DECISION:" + req.decision(), request.getRemoteAddr(),
                null, null, null);
        return Map.of("verificationId", id, "decision", req.decision(), "status", "recorded");
    }
}
