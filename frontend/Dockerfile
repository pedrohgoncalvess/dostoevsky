FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM node:22-alpine

WORKDIR /app

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
ENV SSR_API_BASE_URL=${SSR_API_BASE_URL:-http://backend:8080}

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/build ./build

EXPOSE 3000

CMD ["node", "build/index.js"]
