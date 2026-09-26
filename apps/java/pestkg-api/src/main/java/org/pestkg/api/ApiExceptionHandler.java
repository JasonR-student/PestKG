package org.pestkg.api;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.pestkg.domain.ApiError;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class ApiExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);
    @ExceptionHandler(ReleaseException.class)
    ResponseEntity<Map<String, Object>> release(ReleaseException ex, HttpServletRequest request) {
        String requestId = requestId(request);
        ApiError error = new ApiError(ex.getCode(), ex.getMessage(), ex.getDetails(), requestId);
        return ResponseEntity.status(ex.getStatus()).body(Map.of("error", error));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    ResponseEntity<Map<String, Object>> badRequest(IllegalArgumentException ex, HttpServletRequest request) {
        String requestId = requestId(request);
        return ResponseEntity.badRequest().body(Map.of("error",
                new ApiError("invalid_request", ex.getMessage(), Map.of(), requestId)));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<Map<String, Object>> notFound(NoResourceFoundException ex, HttpServletRequest request) {
        String requestId = requestId(request);
        return ResponseEntity.status(404).body(Map.of("error",
                new ApiError("resource_not_found", "No such resource", Map.of(), requestId)));
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<Map<String, Object>> unexpected(Exception ex, HttpServletRequest request) {
        log.error("unhandled api error", ex);
        String requestId = requestId(request);
        return ResponseEntity.status(500).body(Map.of("error",
                new ApiError("internal_error", "Internal server error", Map.of(), requestId)));
    }

    private static String requestId(HttpServletRequest request) {
        Object value = request.getAttribute(RequestIdFilter.HEADER);
        if (value != null) return String.valueOf(value);
        return request.getHeader(RequestIdFilter.HEADER);
    }
}
