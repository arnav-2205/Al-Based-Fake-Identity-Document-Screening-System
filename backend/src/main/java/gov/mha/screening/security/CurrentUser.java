package gov.mha.screening.security;

import gov.mha.screening.common.ApiException;
import gov.mha.screening.user.User;
import gov.mha.screening.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class CurrentUser {

    private final UserRepository users;

    public User get() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || auth.getName() == null) {
            throw new ApiException(org.springframework.http.HttpStatus.UNAUTHORIZED, "Not authenticated");
        }
        return users.findByOfficerId(auth.getName())
                .orElseThrow(() -> ApiException.notFound("User"));
    }
}
