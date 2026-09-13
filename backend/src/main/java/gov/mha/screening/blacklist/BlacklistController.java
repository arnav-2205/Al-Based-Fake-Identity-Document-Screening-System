package gov.mha.screening.blacklist;

import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/blacklist")
@RequiredArgsConstructor
public class BlacklistController {

    private final BlacklistService service;

    @GetMapping
    @PreAuthorize("hasAnyRole('ADMIN','OFFICER','INVESTIGATOR','AUDITOR')")
    public List<Blacklist> list() {
        return service.all();
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Blacklist add(@RequestBody Blacklist entry) {
        return service.add(entry);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
