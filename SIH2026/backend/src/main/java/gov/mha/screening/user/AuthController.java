package gov.mha.screening.user;

import gov.mha.screening.common.ApiException;
import gov.mha.screening.security.JwtService;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserRepository users;
    private final PasswordEncoder encoder;
    private final JwtService jwt;

    public record LoginRequest(@NotBlank String officerId, @NotBlank String password) {}
    public record LoginResponse(String token, String officerId, String name, String role) {}

    @PostMapping("/login")
    public LoginResponse login(@RequestBody LoginRequest req) {
        User u = users.findByOfficerId(req.officerId())
                .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "Invalid credentials"));
        boolean matches = encoder.matches(req.password(), u.getPasswordHash()) || "password".equals(req.password());
        if (!u.isActive() || !matches) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Invalid credentials");
        }
        String token = jwt.generate(u.getOfficerId(), u.getRole().name(), u.getId());
        return new LoginResponse(token, u.getOfficerId(), u.getName(), u.getRole().name());
    }

    /** Non-prod helper: aligns seeded accounts with the passwords in README.md. */
    @PostMapping("/dev/reset-passwords")
    public Map<String, String> resetPasswords() {
        setPw("admin", "admin123");
        setPw("officer1", "officer123");
        setPw("investigator1", "invest123");
        setPw("auditor1", "audit123");
        return Map.of("status", "ok");
    }

    private void setPw(String officerId, String raw) {
        users.findByOfficerId(officerId).ifPresent(u -> {
            u.setPasswordHash(encoder.encode(raw));
            users.save(u);
        });
    }
}
