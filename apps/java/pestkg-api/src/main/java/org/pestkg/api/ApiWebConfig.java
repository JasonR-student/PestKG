package org.pestkg.api;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ApiWebConfig {
    @Bean
    FilterRegistrationBean<RequestIdFilter> requestIdFilter() {
        FilterRegistrationBean<RequestIdFilter> bean = new FilterRegistrationBean<>();
        bean.setFilter(new RequestIdFilter());
        bean.addUrlPatterns("/*");
        bean.setOrder(1);
        return bean;
    }
}
