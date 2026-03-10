FROM node:20-alpine AS builder
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ARG VITE_API_BASE_URL=/api
ARG VITE_V4T_WS_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_V4T_WS_BASE_URL=$VITE_V4T_WS_BASE_URL
RUN pnpm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/templates/default.conf.template
ENV PRERENDER_FRONTEND_URL=http://frontend:3000
ENV V4T_API_BASE_URL=http://api:8000
ENV NGINX_ENVSUBST_FILTER=PRERENDER_FRONTEND_URL|V4T_API_BASE_URL
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget -qO- http://localhost:3000/ || exit 1
