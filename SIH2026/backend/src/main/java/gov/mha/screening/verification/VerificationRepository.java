package gov.mha.screening.verification;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface VerificationRepository extends JpaRepository<VerificationResult, Long> {
    Optional<VerificationResult> findByDocumentId(Long documentId);
}
