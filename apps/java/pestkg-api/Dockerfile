FROM eclipse-temurin:21-jre

WORKDIR /app
COPY target/pestkg-api-1.0.0-SNAPSHOT.jar app.jar

ENV JAVA_OPTS="-XX:MaxRAMPercentage=75 -Djava.security.egd=file:/dev/./urandom"
EXPOSE 8081
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
