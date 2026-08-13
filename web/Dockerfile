# W7-5 Etapa 4: Frontend containerized deployment (Founder Decision --
# Frontend Hosting, D-171/D-172), consistent with the backend's own
# Dockerfile -- same base image family, same build-then-run discipline,
# same GIT_SHA release identity, separate artifact from the backend.
#
# Uses Next.js `output: "standalone"` (next.config.ts) so the runtime
# image only ships the files `next build` actually traced as needed
# (including instrumentation.ts, W7-5 Etapa 1's fail-fast hook) -- not the
# full node_modules tree.

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

# Release Identity (Technical Design S11): baked in at build time, same
# convention as the backend's Dockerfile -- never a runtime-supplied value,
# so it always matches the code that actually built the running image.
ARG GIT_SHA=unknown
ENV RELEASE_SHA=${GIT_SHA}

# No web/public directory exists in this repository today -- nothing to
# copy. If one is added later, `COPY --from=builder /app/public ./public`
# must be added here too (standalone output does not include it).
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
