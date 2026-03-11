# MCP Playwright — imagen propia necesaria porque node:slim no incluye Chromium.
# Base oficial de Microsoft Playwright con Node 22 + Chromium preinstalado.
FROM mcr.microsoft.com/playwright:v1.50.0-noble

# supergateway convierte el servidor MCP stdio en HTTP/SSE
# para que n8n/Langflow puedan consumirlo como herramienta HTTP.
RUN npm install -g supergateway

EXPOSE 8000

# --headless: sin display server (contenedor headless)
# --host / --port: supergateway escucha en todas las interfaces
ENTRYPOINT ["supergateway", \
  "--stdio", "npx -y @playwright/mcp --headless", \
  "--host", "0.0.0.0", \
  "--port", "8000"]