import { z } from 'zod';
import { executeQuery } from '../database/connection.js';
import { ColumnInfo, TableDetail } from '../database/types.js';

export const describeTableSchema = z.object({
  table: z.string().describe('The name of the table to describe'),
  schema: z.string().optional().default('dbo').describe('The database schema (default: "dbo")'),
});

export const describeTableTool = {
  name: 'describe_table',
  description: 'Retrieve column definitions, data types, nullability, primary keys, foreign keys, and descriptions for a specific table.',
  inputSchema: describeTableSchema,
  handler: async (args: z.infer<typeof describeTableSchema>): Promise<TableDetail> => {
    const schemaName = args.schema || 'dbo';
    const tableName = args.table;

    const sql = `
      SELECT 
        c.COLUMN_NAME AS name,
        c.DATA_TYPE AS type,
        c.CHARACTER_MAXIMUM_LENGTH AS maxLength,
        CASE WHEN c.IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS isNullable,
        CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS isPrimaryKey,
        CASE WHEN fk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS isForeignKey,
        fk.REFERENCED_TABLE AS fkTable,
        fk.REFERENCED_COLUMN AS fkColumn,
        CAST(ep.value AS NVARCHAR(MAX)) AS description
      FROM INFORMATION_SCHEMA.COLUMNS c
      LEFT JOIN (
        SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
          ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
      ) pk ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA AND c.TABLE_NAME = pk.TABLE_NAME AND c.COLUMN_NAME = pk.COLUMN_NAME
      LEFT JOIN (
        SELECT 
          kcu1.TABLE_SCHEMA, kcu1.TABLE_NAME, kcu1.COLUMN_NAME,
          kcu2.TABLE_NAME AS REFERENCED_TABLE, kcu2.COLUMN_NAME AS REFERENCED_COLUMN
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu1 ON rc.CONSTRAINT_NAME = kcu1.CONSTRAINT_NAME
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu2 ON rc.UNIQUE_CONSTRAINT_NAME = kcu2.CONSTRAINT_NAME
      ) fk ON c.TABLE_SCHEMA = fk.TABLE_SCHEMA AND c.TABLE_NAME = fk.TABLE_NAME AND c.COLUMN_NAME = fk.COLUMN_NAME
      LEFT JOIN sys.tables t ON t.name = c.TABLE_NAME AND t.schema_id = SCHEMA_ID(c.TABLE_SCHEMA)
      LEFT JOIN sys.columns sc ON sc.object_id = t.object_id AND sc.name = c.COLUMN_NAME
      LEFT JOIN sys.extended_properties ep ON ep.major_id = t.object_id AND ep.minor_id = sc.column_id AND ep.name = 'MS_Description'
      WHERE c.TABLE_SCHEMA = '${schemaName.replace(/'/g, "''")}'
        AND c.TABLE_NAME = '${tableName.replace(/'/g, "''")}'
      ORDER BY c.ORDINAL_POSITION;
    `;

    interface RawColumnRow {
      name: string;
      type: string;
      maxLength: number | null;
      isNullable: number;
      isPrimaryKey: number;
      isForeignKey: number;
      fkTable: string | null;
      fkColumn: string | null;
      description: string | null;
    }

    const { rows } = await executeQuery<RawColumnRow>(sql);

    const columns: ColumnInfo[] = rows.map((r) => ({
      name: r.name,
      type: r.type,
      maxLength: r.maxLength,
      isNullable: Boolean(r.isNullable),
      isPrimaryKey: Boolean(r.isPrimaryKey),
      isForeignKey: Boolean(r.isForeignKey),
      foreignKeyTarget: r.fkTable && r.fkColumn ? { table: r.fkTable, column: r.fkColumn } : undefined,
      description: r.description || undefined,
    }));

    return {
      table: tableName,
      schema: schemaName,
      columns,
    };
  },
};
