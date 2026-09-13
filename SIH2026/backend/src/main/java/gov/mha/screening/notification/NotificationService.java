package gov.mha.screening.notification;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Service
@Slf4j
@RequiredArgsConstructor
public class NotificationService {

    private final NotificationRepository repo;

    public void raise(Long verificationId, String type, String recipient, String message) {
        try {
            Notification n = new Notification();
            n.setVerificationId(verificationId);
            n.setType(type);
            n.setRecipient(recipient);
            n.setMessage(message);
            n.setStatus("SENT");
            repo.save(n);
        } catch (Throwable e) {
            log.warn("[notification fallback] could not save notification: {}", e.getMessage());
        }
        log.info("[notification] {} -> {}: {}", type, recipient, message);
    }
}
