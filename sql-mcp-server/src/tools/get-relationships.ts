import { z } from 'zod';
import { executeQuery } from '../database/connection.js';
import { RelationshipInfo } from '../database/types.js';

export const getRelationshipsSchema = z.object({
  tableName: z.string().optional().describe('Optional table name to filter foreign key relationships'),
});

export const getRelationshipsTool = {
  name: 'get_relationships',
  description: 'Retrieve foreign key relationships between tables in the database to understand entity relationships.',
  inputSchema: getRelationshipsSchema,
  handler: async (args: z.infer<typeof getRelationshipsSchema>): Promise<RelationshipInfo[]> => {
    let whereClause = '';
    if (args.tableName) {
      const sanitized = args.tableName.replace(/'/g, "''");
      whereClause = `WHERE tp.name = '${sanitized}' OR tr.name = '${sanitized}'`;
    }

    const sql = `
      SELECT 
        fk.name AS constraintName,
        schp.name AS parentSchema,
        tp.name AS parentTable,
        cp.name AS parentColumn,
        schr.name AS referencedSchema,
        tr.name AS referencedTable,
        cr.name AS referencedColumn
      FROM sys.foreign_keys fk
      INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
      INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
      INNER JOIN sys.schemas schp ON tp.schema_id = schp.schema_id
      INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
      INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
      INNER JOIN sys.schemas schr ON tr.schema_id = schr.schema_id
      INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
      ${whereClause}
      ORDER BY parentSchema, parentTable, parentColumn;
    `;

    const { rows } = await executeQuery<RelationshipInfo>(sql);
    return rows;
  },
};
