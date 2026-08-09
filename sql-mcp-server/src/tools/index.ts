import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { listTablesTool } from './list-tables.js';
import { describeTableTool, describeTableSchema } from './describe-table.js';
import { getRelationshipsTool, getRelationshipsSchema } from './get-relationships.js';
import { executeSelectTool, executeSelectSchema } from './execute-select.js';
import { getDatabaseInfoTool } from './get-database-info.js';
import { logger } from '../utils/logger.js';

export function registerTools(server: McpServer): void {
  // 1. list_tables
  server.tool(
    listTablesTool.name,
    listTablesTool.description,
    {},
    async () => {
      try {
        const result = await listTablesTool.handler();
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return { isError: true, content: [{ type: 'text', text: `Error: ${msg}` }] };
      }
    }
  );

  // 2. describe_table
  server.tool(
    describeTableTool.name,
    describeTableTool.description,
    describeTableSchema.shape,
    async (args) => {
      try {
        const result = await describeTableTool.handler(args);
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return { isError: true, content: [{ type: 'text', text: `Error: ${msg}` }] };
      }
    }
  );

  // 3. get_relationships
  server.tool(
    getRelationshipsTool.name,
    getRelationshipsTool.description,
    getRelationshipsSchema.shape,
    async (args) => {
      try {
        const result = await getRelationshipsTool.handler(args);
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return { isError: true, content: [{ type: 'text', text: `Error: ${msg}` }] };
      }
    }
  );

  // 4. execute_select
  server.tool(
    executeSelectTool.name,
    executeSelectTool.description,
    executeSelectSchema.shape,
    async (args) => {
      try {
        const result = await executeSelectTool.handler(args);
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return { isError: true, content: [{ type: 'text', text: `Error: ${msg}` }] };
      }
    }
  );

  // 5. get_database_info
  server.tool(
    getDatabaseInfoTool.name,
    getDatabaseInfoTool.description,
    {},
    async () => {
      try {
        const result = await getDatabaseInfoTool.handler();
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return { isError: true, content: [{ type: 'text', text: `Error: ${msg}` }] };
      }
    }
  );

  logger.info('Registered 5 SQL MCP tools: list_tables, describe_table, get_relationships, execute_select, get_database_info');
}

export async function executeDirectTool(name: string, args: any = {}): Promise<any> {
  switch (name) {
    case 'list_tables':
      return await listTablesTool.handler();
    case 'describe_table':
      return await describeTableTool.handler(args);
    case 'get_relationships':
      return await getRelationshipsTool.handler(args);
    case 'execute_select':
      return await executeSelectTool.handler(args);
    case 'get_database_info':
      return await getDatabaseInfoTool.handler();
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}
