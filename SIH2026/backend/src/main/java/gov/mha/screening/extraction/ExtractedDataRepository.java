package gov.mha.screening.extraction;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ExtractedDataRepository extends JpaRepository<ExtractedData, Long> {
    Optional<ExtractedData> findByDocumentId(Long documentId);
}
