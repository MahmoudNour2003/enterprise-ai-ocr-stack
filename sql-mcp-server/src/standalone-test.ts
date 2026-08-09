import express from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { registerTools } from './tools/index.js';

async function runTest() {
  const app = express();
  const mcpServer = new McpServer({ name: 'test-mcp', version: '1.0.0' });
  registerTools(mcpServer);

  const transports = new Map<string, SSEServerTransport>();

  app.get('/sse', async (req, res) => {
    const transport = new SSEServerTransport('/message', res);
    transports.set(transport.sessionId, transport);
    await mcpServer.connect(transport);
  });

  app.post('/message', async (req, res) => {
    const sessionId = req.query.sessionId as string;
    const transport = transports.get(sessionId);
    if (!transport) {
      res.status(404).send('Session not found');
      return;
    }
    await transport.handlePostMessage(req, res);
  });

  const server = app.listen(3099, async () => {
    console.log('✅ Temporary test MCP Server started on port 3099');

    try {
      const clientTransport = new SSEClientTransport(new URL('http://localhost:3099/sse'));
      const client = new Client({ name: 'test-client', version: '1.0.0' }, { capabilities: {} });

      await client.connect(clientTransport);
      console.log('✅ Client connected via SSE!');

      const toolsList = await client.listTools();
      console.log('✅ Discovered Tools:', toolsList.tools.map(t => t.name));

      console.log('--- Calling list_tables tool ---');
      const res = await client.callTool({ name: 'list_tables', arguments: {} });
      console.log('✅ TOOL RESULT SUCCESS! Data:\n', JSON.stringify(res, null, 2));

      server.close();
      process.exit(0);
    } catch (err) {
      console.error('❌ MCP TEST FAILED:', err);
      server.close();
      process.exit(1);
    }
  });
}

runTest();
