import { executeQuery } from '../database/connection.js';
import { TableInfo } from '../database/types.js';

export const listTablesTool = {
  name: 'list_tables',
  description: 'List all user tables and views in the database, including schema names and table types.',
  inputSchema: {},
  handler: async (): Promise<TableInfo[]> => {
    const sql = `
      SELECT 
        TABLE_SCHEMA AS [schema],
        TABLE_NAME AS [name],
        TABLE_TYPE AS [type]
      FROM INFORMATION_SCHEMA.TABLES
      WHERE TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
      ORDER BY TABLE_SCHEMA, TABLE_NAME;
    `;
    const { rows } = await executeQuery<TableInfo>(sql);
    return rows;
  },
};
