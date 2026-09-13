package gov.mha.screening.user;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByOfficerId(String officerId);
    Optional<User> findByEmail(String email);
}
