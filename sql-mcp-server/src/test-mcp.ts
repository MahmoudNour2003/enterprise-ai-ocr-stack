import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';

async function testMcp() {
  console.log('--- TESTING MCP SERVER LOCALLY ---');
  console.log('Connecting to http://localhost:3001/sse ...');
  
  const transport = new SSEClientTransport(new URL('http://localhost:3001/sse'));
  const client = new Client({ name: 'test-client', version: '1.0.0' }, { capabilities: {} });

  await client.connect(transport);
  console.log('✅ Connected successfully!');

  const tools = await client.listTools();
  console.log('✅ Discovered Tools from MCP:', tools.tools.map(t => t.name));

  console.log('\n--- EXECUTING list_tables TOOL ---');
  const result = await client.callTool({ name: 'list_tables', arguments: {} });
  console.log('✅ Result from list_tables:\n', JSON.stringify(result, null, 2));

  process.exit(0);
}

testMcp().catch(err => {
  console.error('❌ MCP Test Failed:', err);
  process.exit(1);
});
