const sql = require('mssql');
require('dotenv').config();

const dbConfig = {
  user: process.env.DB_USER || 'Cost_Team',
  password: process.env.DB_PASSWORD || 'Cost@User1',
  server: process.env.DB_SERVER || 'PBGM8G',
  port: parseInt(process.env.DB_PORT || '1433', 10),
  database: process.env.DB_NAME || 'Suppier',
  options: {
    encrypt: false,
    trustServerCertificate: true
  },
  pool: {
    max: 10,
    min: 0,
    idleTimeoutMillis: 30000
  }
};

let poolPromise = null;

async function connectDB() {
  if (!poolPromise) {
    try {
      console.log(`🔌 [Database] Connecting to ${dbConfig.server}:${dbConfig.port}/${dbConfig.database}...`);
      poolPromise = await sql.connect(dbConfig);
      console.log('✅ [Database] Connected successfully to SQL Server!');
    } catch (err) {
      console.warn('⚠️ [Database] Connection failed. Using Mock Data Mode for development.');
      console.warn('   Detail:', err.message);
      poolPromise = null;
    }
  }
  return poolPromise;
}

module.exports = {
  sql,
  connectDB
};
