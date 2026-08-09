import mssql from 'mssql';
import fs from 'fs';
import path from 'path';

const sqlFilePath = 'C:/Users/mahmoud1/.gemini/antigravity/brain/2fde2a72-8c0a-4fdf-9f4a-01b1f2c84607/scratch/seed_test_data.sql';

const config: mssql.config = {
  server: '127.0.0.1',
  port: 1433,
  database: 'SPIP_DB',
  user: 'AI_CHAT',
  password: 'AI@123',
  options: {
    encrypt: false,
    trustServerCertificate: true,
  },
};

async function runSeed() {
  console.log('Connecting to SQL Server (SPIP_DB)...');
  const pool = await mssql.connect(config);
  console.log('Connected!');

  const rawSql = fs.readFileSync(sqlFilePath, 'utf8');
  const batches = rawSql.split(/\bGO\b/i);

  for (const b of batches) {
    const trimmed = b.trim();
    if (trimmed && !trimmed.toLowerCase().startsWith('use ')) {
      console.log('Executing batch...');
      await pool.request().query(trimmed);
    }
  }

  console.log('🎉 SEEDING COMPLETED SUCCESSFULLY!');
  process.exit(0);
}

runSeed().catch((err) => {
  console.error('❌ SEEDING FAILED:', err);
  process.exit(1);
});
