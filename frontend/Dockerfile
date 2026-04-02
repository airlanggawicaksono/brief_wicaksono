FROM node:20-alpine AS deps
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --no-frozen-lockfile
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev"]

FROM deps AS prod
RUN pnpm build
CMD ["pnpm", "start"]
