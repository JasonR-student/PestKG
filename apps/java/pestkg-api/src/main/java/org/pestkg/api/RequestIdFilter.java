package org.pestkg.api;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.filter.OncePerRequestFilter;

public class RequestIdFilter extends OncePerRequestFilter {
    public static final String HEADER = "X-Request-ID";
    private static final Logger log = LoggerFactory.getLogger(RequestIdFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String id = request.getHeader(HEADER);
        if (id == null || id.isBlank()) id = UUID.randomUUID().toString();
        request.setAttribute(HEADER, id);
        response.setHeader(HEADER, id);
        long start = System.nanoTime();
        try {
            filterChain.doFilter(request, response);
        } finally {
            String qs = request.getQueryString();
            log.info("{} {}?{} -> {} ({}ms)", request.getMethod(), request.getRequestURI(),
                    qs == null ? "" : qs, response.getStatus(), (System.nanoTime() - start) / 1_000_000);
        }
    }
}
