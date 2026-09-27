# Multi-stage build: compile the Java API from source, then run on a slim JRE.
# Build context should be apps/java so the parent pom and sibling modules are available.
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY pestkg-domain pestkg-domain
COPY pestkg-release pestkg-release
COPY pestkg-graph pestkg-graph
COPY pestkg-ingest pestkg-ingest
COPY pestkg-presentation pestkg-presentation
COPY pestkg-admin pestkg-admin
COPY pestkg-api pestkg-api
RUN mvn -pl pestkg-api -am package -DskipTests -q

FROM eclipse-temurin:21-jre
ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=dev
LABEL org.opencontainers.image.title="PestKG API" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF"
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /src/pestkg-api/target/pestkg-api-1.0.0-SNAPSHOT.jar app.jar
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75 -Djava.security.egd=file:/dev/./urandom"
EXPOSE 18088
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
