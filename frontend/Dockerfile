# ============================================================
# LiveCoach AI — Frontend Dockerfile
# Multi-stage build: development & production
# ============================================================

# --- Stage 1: Base image ---
FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies dulu (cached layer terpisah dari source code)
COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

# --- Stage 2: Development (dipakai saat docker compose up lokal) ---
FROM base AS development
COPY . .
EXPOSE 3000
# --host wajib agar Vite dev server bisa diakses dari luar container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# --- Stage 3: Build untuk production ---
FROM base AS builder
COPY . .
RUN npm run build

# --- Stage 4: Production server (Nginx ringan) ---
FROM nginx:1.27-alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config untuk SPA — semua route diarahkan ke index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
