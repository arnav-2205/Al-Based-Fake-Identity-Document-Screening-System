package gov.mha.screening.document;

import gov.mha.screening.config.AppProperties;
import io.minio.*;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.InputStream;

@Service
@Slf4j
@RequiredArgsConstructor
public class MinioStorageService {

    private final MinioClient client;
    private final AppProperties props;

    private final java.util.Map<String, byte[]> memoryStore = new java.util.concurrent.ConcurrentHashMap<>();

    @PostConstruct
    void ensureBucket() {
        try {
            String bucket = props.minio().bucket();
            boolean exists = client.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
            if (!exists) {
                client.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
                log.info("Created MinIO bucket {}", bucket);
            }
        } catch (Exception e) {
            log.warn("Could not verify/create MinIO bucket: {}", e.getMessage());
        }
    }

    public String put(String objectKey, byte[] data, String contentType) {
        memoryStore.put(objectKey, data);
        try (InputStream in = new ByteArrayInputStream(data)) {
            client.putObject(PutObjectArgs.builder()
                    .bucket(props.minio().bucket())
                    .object(objectKey)
                    .stream(in, data.length, -1)
                    .contentType(contentType == null ? "application/octet-stream" : contentType)
                    .build());
        } catch (Throwable e) {
            log.warn("MinIO upload fallback to memory store for key {}: {}", objectKey, e.getMessage());
        }
        return objectKey;
    }

    public byte[] get(String objectKey) {
        if (memoryStore.containsKey(objectKey)) {
            return memoryStore.get(objectKey);
        }
        try (InputStream in = client.getObject(GetObjectArgs.builder()
                .bucket(props.minio().bucket())
                .object(objectKey)
                .build())) {
            byte[] bytes = in.readAllBytes();
            memoryStore.put(objectKey, bytes);
            return bytes;
        } catch (Throwable e) {
            log.warn("MinIO download fallback for key {}: {}", objectKey, e.getMessage());
            return memoryStore.getOrDefault(objectKey, new byte[0]);
        }
    }
}
