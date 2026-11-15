FROM node:22.23.4-bookworm-slim

ENV NODE_ENV=production
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --omit=dev && npm cache clean --force

COPY . .

RUN node db/init.js

ENV INTERNAL_API_KEY="placeholder_internal_api_key"
ENV INTERNAL_API_URL="http://127.0.0.1:3000"
ENV INTERNAL_API_PORT="3000"
ENV PORT="8080"

ENV flag="EMU{real_flag_on_deployed}"

EXPOSE 8080
USER node
CMD ["node", "start.js"]
