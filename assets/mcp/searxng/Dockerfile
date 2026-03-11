
FROM node:20-slim
RUN npm install -g supergateway mcp-searxng
EXPOSE 8000
ENTRYPOINT ["supergateway", \
  "--stdio", "mcp-searxng", \
  "--host", "0.0.0.0", "--port", "8000"]