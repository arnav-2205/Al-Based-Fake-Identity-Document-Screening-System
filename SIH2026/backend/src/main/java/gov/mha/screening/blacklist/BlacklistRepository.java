package gov.mha.screening.blacklist;

import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;

public interface BlacklistRepository extends JpaRepository<Blacklist, Long> {

    List<Blacklist> findByStatusAndDocumentNumberIgnoreCase(String status, String documentNumber);

    List<Blacklist> findByStatusAndNameIgnoreCaseAndDateOfBirth(String status, String name, LocalDate dob);
}
