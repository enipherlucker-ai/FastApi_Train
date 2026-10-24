FROM node:22-slim AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG API_PROXY_TARGET=http://api:8000
ENV API_PROXY_TARGET=$API_PROXY_TARGET
RUN npm run build

FROM node:22-slim
WORKDIR /web
COPY --from=build /web/.output ./.output
ENV HOST=0.0.0.0 PORT=3000 NODE_ENV=production
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]