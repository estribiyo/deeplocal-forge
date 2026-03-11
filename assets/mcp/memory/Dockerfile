FROM node:20-slim
WORKDIR /app
RUN npm install @modelcontextprotocol/server-memory && \
    npm install -g supergateway
EXPOSE 8000
ENTRYPOINT ["supergateway", \
  "--stdio", "node /app/node_modules/@modelcontextprotocol/server-memory/dist/index.js", \
  "--host", "0.0.0.0", "--port", "8000"]