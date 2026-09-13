package gov.mha.screening.verification;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface FaceEmbeddingRepository extends JpaRepository<FaceEmbedding, Long> {
    List<FaceEmbedding> findAll();
}
