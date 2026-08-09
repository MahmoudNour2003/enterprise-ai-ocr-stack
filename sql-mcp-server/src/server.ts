import dotenv from 'dotenv';
import express from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { registerTools, executeDirectTool } from './tools/index.js';
import { getDbPool, closeDbPool } from './database/connection.js';
import { logger } from './utils/logger.js';

dotenv.config();

const port = parseInt(process.env.MCP_PORT || '3001', 10);
const app = express();

// Initialize MCP Server instance
const mcpServer = new McpServer({
  name: 'sql-bi-assistant-mcp',
  version: '1.0.0',
});

// Register all 5 SQL tools
registerTools(mcpServer);

// Map of active SSE transports by sessionId
const transports = new Map<string, SSEServerTransport>();

// Health check endpoint
app.get('/health', async (_req, res) => {
  try {
    const pool = await getDbPool();
    const isDbConnected = pool.connected;
    res.status(isDbConnected ? 200 : 500).json({
      status: isDbConnected ? 'healthy' : 'unhealthy',
      databaseConnected: isDbConnected,
      activeConnections: transports.size,
      timestamp: new Date().toISOString(),
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    res.status(500).json({
      status: 'unhealthy',
      error: msg,
      timestamp: new Date().toISOString(),
    });
  }
});

// SSE endpoint for n8n MCP Client Tool connection
app.get('/sse', async (req, res) => {
  logger.info('New SSE connection initiated from client');
  
  const transport = new SSEServerTransport('/message', res);
  const sessionId = transport.sessionId;
  transports.set(sessionId, transport);

  req.on('close', () => {
    logger.info(`SSE connection closed for session: ${sessionId}`);
    transports.delete(sessionId);
  });

  await mcpServer.connect(transport);
});

// Message endpoint for SSE bi-directional communication
app.post('/message', async (req, res) => {
  const sessionId = req.query.sessionId as string;
  const transport = transports.get(sessionId);

  if (!transport) {
    res.status(404).send('Session not found');
    return;
  }

  await transport.handlePostMessage(req, res);
});

// Direct HTTP Execution endpoint for tools
app.post('/api/tools/execute', express.json(), async (req, res) => {
  try {
    const { tool, arguments: args } = req.body;
    logger.info(`Received direct tool execution request for '${tool}'`);
    const result = await executeDirectTool(tool, args);
    res.json(result);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    logger.error(`Error executing direct tool '${req.body?.tool}': ${msg}`);
    res.status(500).json({ error: msg });
  }
});

// Start Express HTTP Server
const server = app.listen(port, () => {
  logger.info(`SQL MCP Server running on port ${port}`, {
    sseEndpoint: `http://localhost:${port}/sse`,
    healthEndpoint: `http://localhost:${port}/health`,
  });
});

// Graceful shutdown handling
async function shutdown(signal: string) {
  logger.info(`Received ${signal}, shutting down gracefully...`);
  server.close(() => {
    logger.info('HTTP server closed');
  });

  await closeDbPool();
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
