package org.pestkg.api;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import org.springframework.stereotype.Service;

@Service
public class CursorService {
    public String fingerprint(CsvDataStore.UseQuery query) {
        return sha256(query.toString());
    }

    public String encode(int offset, String release, String fingerprint) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString((release + "|" + fingerprint + "|" + offset).getBytes(StandardCharsets.UTF_8));
    }

    public int decode(String cursor, String release, String fingerprint) {
        if (cursor == null || cursor.isBlank()) return 0;
        String value;
        try { value = new String(Base64.getUrlDecoder().decode(cursor), StandardCharsets.UTF_8); }
        catch (IllegalArgumentException ex) { throw new ReleaseException("cursor_invalid", "Cursor is invalid", 400, null); }
        String[] parts = value.split("\\|", 3);
        if (parts.length != 3) throw new ReleaseException("cursor_invalid", "Cursor is invalid", 400, null);
        if (!release.equals(parts[0])) throw new ReleaseException("cursor_release_mismatch", "Cursor belongs to another release", 400, null);
        if (!fingerprint.equals(parts[1])) throw new ReleaseException("cursor_filter_mismatch", "Cursor belongs to another filter", 400, null);
        try { return Math.max(0, Integer.parseInt(parts[2])); }
        catch (NumberFormatException ex) { throw new ReleaseException("cursor_invalid", "Cursor offset is invalid", 400, null); }
    }

    private static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder();
            for (byte item : digest) result.append(String.format("%02x", item));
            return result.toString();
        } catch (Exception ex) { throw new IllegalStateException(ex); }
    }
}
