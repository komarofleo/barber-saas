# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Копирование package.json и установка зависимостей
COPY web/frontend/package.json web/frontend/vite.config.ts web/frontend/tsconfig.json web/frontend/tsconfig.node.json ./
RUN npm install

# Копирование исходников и сборка
COPY web/frontend/ ./
RUN npm run build

# Production stage
FROM nginx:alpine

# Копирование конфигурации nginx
COPY web/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Копирование собранного приложения
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

