import { z } from 'zod';
import { executeQueryWithContext } from '../database/connection.js';
import { validateSelectQuery } from '../validation/sql-validator.js';
import { QueryResult } from '../database/types.js';
import { logger } from '../utils/logger.js';

export const executeSelectSchema = z.object({
  sql: z.string().describe('The SELECT SQL statement to execute. Only SELECT queries are permitted.'),
  userId: z.number().optional().describe('Optional domain user ID for RLS session context.'),
});

export const executeSelectTool = {
  name: 'execute_select',
  description: 'Execute a read-only SELECT SQL query against SQL Server. Enforces security validation, 30-second timeout, and 1000-row cap. Optionally accepts a userId for session context.',
  inputSchema: executeSelectSchema,
  handler: async (args: z.infer<typeof executeSelectSchema>): Promise<QueryResult> => {
    const validation = validateSelectQuery(args.sql);

    if (!validation.valid || !validation.sanitizedSql) {
      logger.warn('Query security check rejected SQL execution', { sql: args.sql, reason: validation.error });
      throw new Error(`SQL Validation Error: ${validation.error}`);
    }

    logger.info('Executing validated SELECT query', { sanitizedSql: validation.sanitizedSql, userId: args.userId });

    const { rows, executionTimeMs } = await executeQueryWithContext(validation.sanitizedSql, args.userId);

    return {
      rowCount: rows.length,
      rows,
      executionTimeMs,
    };
  },
};
