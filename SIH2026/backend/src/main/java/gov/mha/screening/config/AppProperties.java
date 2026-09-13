package gov.mha.screening.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.List;

@ConfigurationProperties(prefix = "app")
public record AppProperties(
        Jwt jwt,
        Cors cors,
        Minio minio,
        Ai ai,
        Risk risk,
        Blockchain blockchain
) {
    public record Jwt(String secret, long expirationMs) {}

    public record Cors(List<String> allowedOrigins) {}

    public record Minio(String endpoint, String accessKey, String secretKey, String bucket) {}

    public record Ai(String baseUrl, long timeoutMs) {}

    public record Risk(Weights weights, Thresholds thresholds) {
        public record Weights(int tampering, int face, int validation, int blacklist,
                              int multiIdentity, int liveness) {}
        public record Thresholds(double faceMatch, double tamperFlag) {}
    }

    public record Blockchain(boolean enabled, String channel, String chaincode) {}
}
