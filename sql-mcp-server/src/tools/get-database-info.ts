import { executeQuery } from '../database/connection.js';
import { DatabaseInfo } from '../database/types.js';

export const getDatabaseInfoTool = {
  name: 'get_database_info',
  description: 'Retrieve general metadata about the database, including SQL Server version, database name, available schemas, and views.',
  inputSchema: {},
  handler: async (): Promise<DatabaseInfo> => {
    const metaSql = `
      SELECT 
        DB_NAME() AS databaseName,
        @@VERSION AS sqlVersion,
        CONVERT(NVARCHAR(128), DATABASEPROPERTYEX(DB_NAME(), 'Collation')) AS collation;
    `;

    const schemasSql = `
      SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA
      WHERE SCHEMA_NAME NOT IN ('sys', 'INFORMATION_SCHEMA')
      ORDER BY SCHEMA_NAME;
    `;

    const viewsSql = `
      SELECT TABLE_SCHEMA + '.' + TABLE_NAME AS viewName
      FROM INFORMATION_SCHEMA.VIEWS
      WHERE TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
      ORDER BY TABLE_SCHEMA, TABLE_NAME;
    `;

    const [metaRes, schemasRes, viewsRes] = await Promise.all([
      executeQuery<{ databaseName: string; sqlVersion: string; collation: string }>(metaSql),
      executeQuery<{ SCHEMA_NAME: string }>(schemasSql),
      executeQuery<{ viewName: string }>(viewsSql),
    ]);

    const meta = metaRes.rows[0] || { databaseName: 'Unknown', sqlVersion: 'Unknown', collation: 'Unknown' };

    return {
      databaseName: meta.databaseName,
      sqlVersion: meta.sqlVersion,
      collation: meta.collation,
      schemas: schemasRes.rows.map((r) => r.SCHEMA_NAME),
      views: viewsRes.rows.map((r) => r.viewName),
    };
  },
};
