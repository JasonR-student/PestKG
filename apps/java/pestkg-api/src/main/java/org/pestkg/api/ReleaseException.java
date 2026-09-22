package org.pestkg.api;

public class ReleaseException extends RuntimeException {
    private final String code;
    private final int status;
    private final Object details;

    public ReleaseException(String code, String message, int status, Object details) {
        super(message);
        this.code = code;
        this.status = status;
        this.details = details;
    }

    public String getCode() { return code; }
    public int getStatus() { return status; }
    public Object getDetails() { return details; }
}
