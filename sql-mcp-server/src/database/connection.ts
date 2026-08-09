import mssql from 'mssql';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { logger } from '../utils/logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env from sql-mcp-server folder or root AI-BI-Assistant folder
dotenv.config({ path: path.resolve(__dirname, '../../.env') });
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

let pool: mssql.ConnectionPool | null = null;

export async function getDbPool(): Promise<mssql.ConnectionPool> {
  if (pool && pool.connected) {
    return pool;
  }

  const config: mssql.config = {
    server: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '1433', 10),
    database: process.env.DB_NAME || 'master',
    user: process.env.DB_USER || 'sa',
    password: process.env.DB_PASSWORD || '',
    options: {
      encrypt: process.env.DB_ENCRYPT === 'true',
      trustServerCertificate: process.env.DB_TRUST_SERVER_CERT !== 'false',
      requestTimeout: parseInt(process.env.DB_REQUEST_TIMEOUT || '30000', 10),
      connectTimeout: parseInt(process.env.DB_CONNECT_TIMEOUT || '15000', 10),
    },
    pool: {
      min: 2,
      max: 10,
      idleTimeoutMillis: 30000,
    },
  };

  let attempts = 0;
  const maxAttempts = 3;

  while (attempts < maxAttempts) {
    try {
      attempts++;
      logger.info(`Connecting to SQL Server (attempt ${attempts}/${maxAttempts})...`, {
        server: config.server,
        database: config.database,
      });

      pool = await new mssql.ConnectionPool(config).connect();
      logger.info('Connected to SQL Server successfully');
      
      pool.on('error', (err) => {
        logger.error('SQL Server pool error', { error: err.message });
      });

      return pool;
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      logger.warn(`Failed to connect to SQL Server on attempt ${attempts}`, { error: errorMsg });
      if (attempts >= maxAttempts) {
        logger.error('Exhausted all SQL Server connection attempts');
        throw new Error(`Database connection failed: ${errorMsg}`);
      }
      await new Promise((res) => setTimeout(res, 2000 * attempts));
    }
  }

  throw new Error('Database connection uninitialized');
}

export async function executeQuery<T = Record<string, unknown>>(
  sql: string
): Promise<{ rows: T[]; executionTimeMs: number }> {
  const activePool = await getDbPool();
  const startTime = Date.now();

  try {
    const request = activePool.request();
    const result = await request.query<T>(sql);
    const executionTimeMs = Date.now() - startTime;

    return {
      rows: result.recordset || [],
      executionTimeMs,
    };
  } catch (err: unknown) {
    const executionTimeMs = Date.now() - startTime;
    const errorMsg = err instanceof Error ? err.message : String(err);
    logger.error('SQL query execution failed', { sql, error: errorMsg, executionTimeMs });
    throw err;
  }
}

export async function executeQueryWithContext<T = Record<string, unknown>>(
  sql: string,
  userId?: number
): Promise<{ rows: T[]; executionTimeMs: number }> {
  const activePool = await getDbPool();
  const startTime = Date.now();

  try {
    const request = activePool.request();

    let finalSql = sql;
    const activeUserId = (userId !== undefined && userId !== null) ? userId : 5;
    logger.info('Executing atomic batch with SESSION_CONTEXT for activeUserId', { activeUserId });
    finalSql = `EXEC sp_set_session_context @key = N'UserId', @value = ${activeUserId};\n${sql}`;

    const result = await request.query<T>(finalSql);
    const executionTimeMs = Date.now() - startTime;

    logger.info('Query execution raw result', { 
      recordsetLen: result.recordset?.length, 
      recordsetsCount: result.recordsets?.length,
      lengths: result.recordsets?.map(r => r.length)
    });

    let rows: T[] = [];
    if (result.recordsets && result.recordsets.length > 0) {
      // Find the non-empty recordset or default to the last one
      const populated = result.recordsets.find(rs => rs.length > 0);
      rows = (populated || result.recordsets[result.recordsets.length - 1] || []) as T[];
    } else if (result.recordset) {
      rows = result.recordset;
    }

    return {
      rows,
      executionTimeMs,
    };
  } catch (err: unknown) {
    const executionTimeMs = Date.now() - startTime;
    const errorMsg = err instanceof Error ? err.message : String(err);
    logger.error('SQL query execution failed', { sql, error: errorMsg, executionTimeMs, userId });
    throw err;
  }
}

export async function closeDbPool(): Promise<void> {
  if (pool) {
    await pool.close();
    pool = null;
    logger.info('SQL Server connection pool closed');
  }
}
