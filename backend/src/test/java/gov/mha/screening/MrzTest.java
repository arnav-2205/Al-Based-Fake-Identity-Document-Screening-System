package gov.mha.screening;

import gov.mha.screening.validation.Mrz;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class MrzTest {

    // Canonical ICAO 9303 Appendix example (Angela Zoe Smith / Utopia).
    private static final String MRZ =
            "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n" +
            "L898902C36UTO7408122F1204159ZE184226B<<<<<10";

    @Test
    void checkDigitAlgorithm() {
        // "L898902C3" with check digit 6
        assertEquals(6, Mrz.checkDigit("L898902C3"));
    }

    @Test
    void parsesAndValidatesKnownGoodMrz() {
        var parsed = Mrz.parseTd3(MRZ).orElseThrow();
        assertTrue(parsed.documentNumberValid(), "doc number check digit");
        assertTrue(parsed.dobValid(), "dob check digit");
        assertTrue(parsed.expiryValid(), "expiry check digit");
        assertEquals("ERIKSSON", parsed.surname());
    }

    @Test
    void detectsManipulatedPassportNumber() {
        String tampered = MRZ.replace("L898902C36", "L898902C99");
        var parsed = Mrz.parseTd3(tampered).orElseThrow();
        assertFalse(parsed.documentNumberValid(), "manipulated number must fail checksum");
    }
}
