# Multi-stage build for production optimization
FROM node:20-alpine AS builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_URL=
ARG NEXTAUTH_URL=

# Set environment variables for build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXTAUTH_URL=$NEXTAUTH_URL
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application
RUN pnpm run build

# Production stage
FROM node:20-alpine

# Set timezone
ENV TZ=UTC

# Install runtime dependencies
RUN apk add --no-cache \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/UTC /etc/localtime \
    && echo "UTC" > /etc/timezone

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# Expose port
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Run the application
CMD ["node", "server.js"]
