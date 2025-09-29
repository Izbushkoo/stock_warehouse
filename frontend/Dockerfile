# syntax=docker/dockerfile:1

FROM node:20-alpine AS base
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN npm install
COPY . .

FROM base AS dev
ENV VITE_DEV_SERVER_PORT=5173
CMD ["sh", "-c", "npm run dev -- --host 0.0.0.0 --port ${VITE_DEV_SERVER_PORT}"]

FROM base AS build
ARG VITE_API_BASE_URL
ARG VITE_PREVIEW_PORT=4173
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_PREVIEW_PORT=${VITE_PREVIEW_PORT}
RUN npm run build

FROM node:20-alpine AS preview
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
ENV PREVIEW_PORT=4173
EXPOSE 4173
CMD ["sh", "-c", "serve -s dist -l ${PREVIEW_PORT}"]
