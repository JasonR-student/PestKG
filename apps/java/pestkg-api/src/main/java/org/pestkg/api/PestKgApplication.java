package org.pestkg.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(PestKgProperties.class)
public class PestKgApplication {
    public static void main(String[] args) {
        SpringApplication.run(PestKgApplication.class, args);
    }
}
