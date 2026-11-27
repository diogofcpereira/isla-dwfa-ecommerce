# syntax=docker/dockerfile:1
# frontend/Dockerfile — a SPA em produção: o Node só compila; quem serve é o Nginx.

# ---------- fase 1: build (Node) ----------
FROM node:22-alpine AS build
WORKDIR /app

# Primeiro só o package*.json: o `npm ci` fica em cache enquanto as dependências não mudam.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .
# "" → os pedidos saem relativos (/api/v1/...): a SPA e a API ficam na mesma origem,
# atrás do Nginx, e o browser nem precisa de CORS.
ENV VITE_API_URL=""
# type-check + vite build: um erro de tipos impede a imagem de ser criada.
RUN npm run build

# ---------- fase 2: runtime (Nginx) ----------
# 1.30 = a linha "stable" atual do Nginx (a 1.28 deixou de receber correções na imagem).
FROM nginx:1.30-alpine AS runtime

# Extra do M2 (segurança da imagem): aplica as correções de segurança publicadas desde que a
# imagem base foi gerada. O Trivy, no CI, confirma que não ficam vulnerabilidades HIGH/CRITICAL
# com correção disponível.
RUN apk upgrade --no-cache

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY nginx/spa-security-headers.conf /etc/nginx/snippets/spa-security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
# A imagem oficial já arranca com: nginx -g 'daemon off;'