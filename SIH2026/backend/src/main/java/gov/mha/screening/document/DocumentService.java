package gov.mha.screening.document;

import gov.mha.screening.common.ApiException;
import gov.mha.screening.common.HashUtil;
import gov.mha.screening.security.CurrentUser;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documents;
    private final MinioStorageService storage;
    private final CurrentUser currentUser;

    public Document upload(String documentType, MultipartFile file) {
        if (file == null || file.isEmpty()) throw ApiException.badRequest("Empty file");
        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException e) {
            throw ApiException.badRequest("Could not read upload");
        }
        String hash = HashUtil.sha256(bytes);
        String ext = extension(file.getOriginalFilename());
        String key = "docs/" + UUID.randomUUID() + ext;
        storage.put(key, bytes, file.getContentType());

        Document d = new Document();
        d.setDocumentType(documentType == null ? "PASSPORT" : documentType.toUpperCase());
        d.setFileReference(key);
        d.setFileHash(hash);
        d.setUploadedBy(currentUser.get().getId());
        return documents.save(d);
    }

    public Document require(Long id) {
        return documents.findById(id).orElseThrow(() -> ApiException.notFound("Document " + id));
    }

    private String extension(String name) {
        if (name == null) return "";
        int i = name.lastIndexOf('.');
        return i >= 0 ? name.substring(i) : "";
    }
}
