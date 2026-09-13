package gov.mha.screening.audit;

import gov.mha.screening.verification.VerificationService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/audit")
@RequiredArgsConstructor
public class AuditController {

    private final AuditService auditService;
    private final VerificationService verificationService;

    @GetMapping("/{verificationId}")
    @PreAuthorize("hasAnyRole('ADMIN','INVESTIGATOR','AUDITOR')")
    public List<AuditLog> forVerification(@PathVariable Long verificationId) {
        return auditService.trail(verificationId);
    }

    @GetMapping
    @PreAuthorize("hasAnyRole('ADMIN','INVESTIGATOR','AUDITOR')")
    public List<AuditLog> all() {
        return auditService.all();
    }

    @GetMapping("/{verificationId}/integrity-check")
    @PreAuthorize("hasAnyRole('ADMIN','INVESTIGATOR','AUDITOR')")
    public Map<String, Object> integrity(@PathVariable Long verificationId) {
        return verificationService.integrityCheck(verificationId);
    }
}
