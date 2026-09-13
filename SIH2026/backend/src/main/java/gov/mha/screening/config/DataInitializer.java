package gov.mha.screening.config;

import gov.mha.screening.blacklist.Blacklist;
import gov.mha.screening.blacklist.BlacklistRepository;
import gov.mha.screening.user.Role;
import gov.mha.screening.user.User;
import gov.mha.screening.user.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.List;

@Component
@Slf4j
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final BlacklistRepository blacklistRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) {
        if (userRepository.count() == 0) {
            log.info("Seeding default demo users into database...");
            String encodedPass = passwordEncoder.encode("password");

            User admin = new User();
            admin.setOfficerId("admin");
            admin.setName("System Administrator");
            admin.setEmail("admin@ssb.gov.in");
            admin.setPasswordHash(passwordEncoder.encode("admin123"));
            admin.setRole(Role.ADMIN);
            admin.setCheckpointId("HQ");
            admin.setActive(true);

            User officer = new User();
            officer.setOfficerId("officer1");
            officer.setName("Officer R. Sharma");
            officer.setEmail("officer1@ssb.gov.in");
            officer.setPasswordHash(passwordEncoder.encode("officer123"));
            officer.setRole(Role.OFFICER);
            officer.setCheckpointId("ICP-ATTARI");
            officer.setActive(true);

            User investigator = new User();
            investigator.setOfficerId("investigator1");
            investigator.setName("Investigator P. Nair");
            investigator.setEmail("investigator1@ssb.gov.in");
            investigator.setPasswordHash(passwordEncoder.encode("invest123"));
            investigator.setRole(Role.INVESTIGATOR);
            investigator.setCheckpointId("HQ");
            investigator.setActive(true);

            User auditor = new User();
            auditor.setOfficerId("auditor1");
            auditor.setName("Auditor S. Rao");
            auditor.setEmail("auditor1@ssb.gov.in");
            auditor.setPasswordHash(passwordEncoder.encode("audit123"));
            auditor.setRole(Role.AUDITOR);
            auditor.setCheckpointId("HQ");
            auditor.setActive(true);

            userRepository.saveAll(List.of(admin, officer, investigator, auditor));
            log.info("Successfully seeded 4 demo users.");
        }

        if (blacklistRepository.count() == 0) {
            log.info("Seeding default watchlist entries into database...");
            Blacklist b1 = new Blacklist();
            b1.setDocumentNumber("P1234567");
            b1.setDocumentType("PASSPORT");
            b1.setName("John Fictitious");
            b1.setDateOfBirth(LocalDate.of(1985, 4, 12));
            b1.setReason("INTERPOL Red Notice — Identity Fraud");
            b1.setStatus("ACTIVE");

            Blacklist b2 = new Blacklist();
            b2.setDocumentNumber("X9988776");
            b2.setDocumentType("PASSPORT");
            b2.setName("Anon Suspect");
            b2.setDateOfBirth(LocalDate.of(1990, 11, 2));
            b2.setReason("Watchlist — Multiple forged border entries");
            b2.setStatus("ACTIVE");

            Blacklist b3 = new Blacklist();
            b3.setDocumentNumber("V0001111");
            b3.setDocumentType("VISA");
            b3.setName("Test Forged Visa");
            b3.setDateOfBirth(LocalDate.of(1978, 1, 30));
            b3.setReason("Known counterfeit visa serial batch");
            b3.setStatus("ACTIVE");

            blacklistRepository.saveAll(List.of(b1, b2, b3));
            log.info("Successfully seeded 3 watchlist entries.");
        }
    }
}
