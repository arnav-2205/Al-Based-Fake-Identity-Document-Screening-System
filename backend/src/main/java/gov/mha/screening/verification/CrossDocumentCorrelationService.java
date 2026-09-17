package gov.mha.screening.verification;

import gov.mha.screening.document.Document;
import gov.mha.screening.extraction.ExtractedData;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class CrossDocumentCorrelationService {

    public CorrelationResult compare(
            Document currentDocument,
            ExtractedData currentData,
            Document previousDocument,
            ExtractedData previousData
    ) {
        int matches = 0;
        int conflicts = 0;
        int available = 0;

        List<String> matchedFields = new ArrayList<>();
        List<String> conflictingFields = new ArrayList<>();

        if (same(currentData.getName(), previousData.getName())) {
            matches++;
            available++;
            matchedFields.add("Name");
        } else if (present(currentData.getName()) && present(previousData.getName())) {
            conflicts++;
            available++;
            conflictingFields.add("Name");
        }

        if (currentData.getDateOfBirth() != null && previousData.getDateOfBirth() != null) {
            available++;
            if (currentData.getDateOfBirth().equals(previousData.getDateOfBirth())) {
                matches++;
                matchedFields.add("Date of Birth");
            } else {
                conflicts++;
                conflictingFields.add("Date of Birth");
            }
        }

        if (same(currentData.getNationality(), previousData.getNationality())) {
            matches++;
            available++;
            matchedFields.add("Nationality");
        } else if (present(currentData.getNationality()) && present(previousData.getNationality())) {
            conflicts++;
            available++;
            conflictingFields.add("Nationality");
        }

        if (same(currentData.getGender(), previousData.getGender())) {
            matches++;
            available++;
            matchedFields.add("Gender");
        } else if (present(currentData.getGender()) && present(previousData.getGender())) {
            conflicts++;
            available++;
            conflictingFields.add("Gender");
        }

        String status;

        if (conflicts > 0) {
            status = "MISMATCH";
        } else if (matches >= 2) {
            status = "MATCH";
        } else {
            status = "NOT_ENOUGH_EVIDENCE";
        }

        return new CorrelationResult(
                status,
                previousDocument.getId(),
                previousDocument.getDocumentType(),
                matches,
                conflicts,
                available,
                matchedFields,
                conflictingFields
        );
    }

    private boolean same(String a, String b) {
        return present(a) && present(b)
                && a.trim().equalsIgnoreCase(b.trim());
    }

    private boolean present(String value) {
        return value != null && !value.trim().isEmpty();
    }

    public record CorrelationResult(
            String status,
            Long previousDocumentId,
            String previousDocumentType,
            int matchedFields,
            int conflictingFields,
            int availableFields,
            List<String> matchedFieldsList,
            List<String> conflictingFieldsList
    ) {}
}