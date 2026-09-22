package org.pestkg.api;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.pestkg.domain.ApiError;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(ReleaseException.class)
    ResponseEntity<Map<String, Object>> release(ReleaseException ex, HttpServletRequest request) {
        String requestId = request.getHeader(RequestIdFilter.HEADER);
        ApiError error = new ApiError(ex.getCode(), ex.getMessage(), ex.getDetails(), requestId);
        return ResponseEntity.status(ex.getStatus()).body(Map.of("error", error));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    ResponseEntity<Map<String, Object>> badRequest(IllegalArgumentException ex, HttpServletRequest request) {
        String requestId = request.getHeader(RequestIdFilter.HEADER);
        return ResponseEntity.badRequest().body(Map.of("error",
                new ApiError("invalid_request", ex.getMessage(), Map.of(), requestId)));
    }
}
