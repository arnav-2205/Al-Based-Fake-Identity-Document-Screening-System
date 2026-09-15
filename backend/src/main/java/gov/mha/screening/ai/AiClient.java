package gov.mha.screening.ai;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.Map;

/**
 * Non-blocking parallel calls to the Python AI service (Spec Part 5, step 4).
 * OCR, tamper detection and face verification run simultaneously via Mono.zip.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class AiClient {

    private final WebClient aiWebClient;

    public AiDtos.AiBundle analyzeAll(byte[] documentImage, byte[] liveFaceImage) {
        Mono<AiDtos.OcrResult> ocr = ocr(documentImage).onErrorResume(this::fallbackOcr);
        Mono<AiDtos.TamperResult> tamper = tamper(documentImage).onErrorResume(this::fallbackTamper);
        Mono<AiDtos.FaceResult> face = face(documentImage, liveFaceImage).onErrorResume(this::fallbackFace);

        return Mono.zip(ocr, tamper, face)
                .map(t -> new AiDtos.AiBundle(t.getT1(), t.getT2(), t.getT3()))
                .block();
    }

    public AiDtos.OcrResult extractOcr(byte[] image) {
        return ocr(image).onErrorResume(this::fallbackOcr).block();
    }

    private static ByteArrayResource file(byte[] data, String filename) {
        return new ByteArrayResource(data) {
            @Override public String getFilename() { return filename; }
        };
    }

    private Mono<AiDtos.OcrResult> ocr(byte[] image) {
        MultipartBodyBuilder b = new MultipartBodyBuilder();
        b.part("file", file(image, "document.jpg"));
        return aiWebClient.post().uri("/ocr/extract")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(b.build()))
                .retrieve().bodyToMono(AiDtos.OcrResult.class);
    }

    private Mono<AiDtos.TamperResult> tamper(byte[] image) {
        MultipartBodyBuilder b = new MultipartBodyBuilder();
        b.part("file", file(image, "document.jpg"));
        return aiWebClient.post().uri("/tamper/analyze")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(b.build()))
                .retrieve().bodyToMono(AiDtos.TamperResult.class);
    }

    private Mono<AiDtos.FaceResult> face(byte[] docImage, byte[] liveImage) {
        MultipartBodyBuilder b = new MultipartBodyBuilder();
        b.part("doc_photo", file(docImage, "doc.jpg"));
        if (liveImage != null) {
            b.part("live_photo", file(liveImage, "live.jpg"));
        }
        return aiWebClient.post().uri("/face/verify")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(b.build()))
                .retrieve().bodyToMono(AiDtos.FaceResult.class);
    }

    // --- graceful degradation when the AI service is unreachable -----------
    private Mono<AiDtos.OcrResult> fallbackOcr(Throwable e) {
        log.warn("OCR call failed, using fallback: {}", e.getMessage());
        return Mono.just(new AiDtos.OcrResult(
                null, Map.of(), Map.of(), 0.0, Map.of(), Map.of(),
                false, Map.of(), List.of("AI service unavailable — OCR skipped"),
                "UNKNOWN", "NATIONAL_ID", "NATIONAL_ID_CARD", List.of(), List.of(),
                "UNKNOWN", false, false, false, "NOT_AVAILABLE", "NOT_AVAILABLE",
                null, "NOT_APPLICABLE", List.of(), false, false, "NOT_AVAILABLE",
                "NONE", null, "NOT_AVAILABLE", "UNKNOWN", 0.0,
                new AiDtos.VisaResult(null, null, "UNKNOWN", null, null, null, null, null, null, "NOT_APPLICABLE", List.of("AI service unavailable")),
                new AiDtos.DrivingLicenceResult(null, null, null, null, null, null, null, List.of(), "NOT_AVAILABLE", "NOT_APPLICABLE", List.of("AI service unavailable")),
                new AiDtos.NationalIdResult(null, null, null, "UNKNOWN", null, null, null, null, null, "NOT_AVAILABLE", "NOT_AVAILABLE", "NOT_APPLICABLE", List.of("AI service unavailable")),
                new AiDtos.PermitResult(null, null, null, null, null, null, null, null, null, null, null, "NOT_APPLICABLE", List.of("AI service unavailable"))));



    }

    private Mono<AiDtos.TamperResult> fallbackTamper(Throwable e) {
        log.warn("Tamper call failed, using fallback: {}", e.getMessage());
        return Mono.just(new AiDtos.TamperResult(
                0.0, 0.0, 0.0, 0.0,
                null, null, null, null,
                null, Map.of(),
                List.of("AI service unavailable — tamper analysis skipped")));
    }

    private Mono<AiDtos.FaceResult> fallbackFace(Throwable e) {
        log.warn("Face call failed, using fallback: {}", e.getMessage());
        return Mono.just(new AiDtos.FaceResult(0.0, "UNKNOWN", "UNKNOWN", List.of(),
                List.of("AI service unavailable — face verification skipped")));
    }
}
