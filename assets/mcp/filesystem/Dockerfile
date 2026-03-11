FROM node:20-slim
WORKDIR /app
RUN npm install @modelcontextprotocol/server-filesystem && \
    npm install -g supergateway
EXPOSE 8000
ENTRYPOINT ["supergateway", \
  "--stdio", "node /app/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js /mcp/fs", \
  "--host", "0.0.0.0", "--port", "8000"]