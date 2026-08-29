FROM node:22-alpine AS build
WORKDIR /app

# The lockfile is committed and `npm ci` installs from it exactly. `npm install`
# without it re-resolves every caret range at build time, so two builds of the
# same commit could ship different dependency versions.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npx tsc --noEmit && npx vite build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
