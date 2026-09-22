FROM node:24-bookworm-slim AS build

ARG NPM_REGISTRY=https://registry.npmjs.org
ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=dev

WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm config set registry "$NPM_REGISTRY" && npm ci
COPY apps/web/ ./
RUN npm run build

FROM nginx:1.29-alpine AS runtime

ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=dev

LABEL org.opencontainers.image.title="PestKG Web" \
      org.opencontainers.image.description="Bilingual research portal for the multicountry pesticide knowledge graph" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.licenses="MIT"

COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
  CMD ["wget", "--quiet", "--spider", "http://127.0.0.1/healthz"]
