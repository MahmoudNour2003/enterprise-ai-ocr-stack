export interface TableInfo {
  schema: string;
  name: string;
  type: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  maxLength: number | null;
  isNullable: boolean;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
  foreignKeyTarget?: {
    table: string;
    column: string;
  };
  description?: string;
}

export interface TableDetail {
  table: string;
  schema: string;
  columns: ColumnInfo[];
}

export interface RelationshipInfo {
  constraintName: string;
  parentSchema: string;
  parentTable: string;
  parentColumn: string;
  referencedSchema: string;
  referencedTable: string;
  referencedColumn: string;
}

export interface DatabaseInfo {
  databaseName: string;
  sqlVersion: string;
  schemas: string[];
  views: string[];
  collation: string;
}

export interface QueryResult {
  rowCount: number;
  rows: Record<string, unknown>[];
  executionTimeMs: number;
}
