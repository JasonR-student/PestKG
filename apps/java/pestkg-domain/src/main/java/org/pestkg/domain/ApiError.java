package org.pestkg.domain;

public record ApiError(String code, String message, Object details, String requestId) {
}
