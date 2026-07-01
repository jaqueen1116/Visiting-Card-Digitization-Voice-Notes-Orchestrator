# Stage 1: Build static assets
FROM node:18-alpine AS build

WORKDIR /app

ARG VITE_API_URL=http://127.0.0.1:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build the Vite React production bundle
RUN npm run build

# Stage 2: Serve via Nginx
FROM nginx:alpine

# Copy built dist files
COPY --from=build /app/dist /usr/share/nginx/html

# Overwrite default Nginx configuration to support SPA routing (fallback to index.html)
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
