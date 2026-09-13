package gov.mha.screening.blacklist;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Service
@Slf4j
@RequiredArgsConstructor
public class BlacklistService {

    private final BlacklistRepository repo;

    public record Hit(boolean matched, String reason) {}

    /** Lookup watchlist entries from database with Redis fallback. */
    public Hit check(String documentNumber, String name, LocalDate dob) {
        try {
            return checkCached(documentNumber, name, dob);
        } catch (Throwable e) {
            log.warn("Cache lookup failed, performing direct DB check: {}", e.getMessage());
            return checkDirect(documentNumber, name, dob);
        }
    }

    @Cacheable(value = "blacklist", key = "#documentNumber + '|' + #name + '|' + #dob")
    public Hit checkCached(String documentNumber, String name, LocalDate dob) {
        return checkDirect(documentNumber, name, dob);
    }

    private Hit checkDirect(String documentNumber, String name, LocalDate dob) {
        if (documentNumber != null && !documentNumber.isBlank()) {
            List<Blacklist> byNumber = repo.findByStatusAndDocumentNumberIgnoreCase("ACTIVE", documentNumber.trim());
            if (!byNumber.isEmpty()) {
                return new Hit(true, "Blacklisted document number: " + byNumber.get(0).getReason());
            }
        }
        if (name != null && dob != null) {
            List<Blacklist> byIdentity = repo.findByStatusAndNameIgnoreCaseAndDateOfBirth("ACTIVE", name.trim(), dob);
            if (!byIdentity.isEmpty()) {
                return new Hit(true, "Blacklisted identity (name + DOB): " + byIdentity.get(0).getReason());
            }
        }
        return new Hit(false, "No blacklist match");
    }

    public List<Blacklist> all() { return repo.findAll(); }

    public Blacklist add(Blacklist entry) {
        if (entry.getStatus() == null) entry.setStatus("ACTIVE");
        return repo.save(entry);
    }

    public Optional<Blacklist> get(Long id) { return repo.findById(id); }

    public void delete(Long id) { repo.deleteById(id); }
}
