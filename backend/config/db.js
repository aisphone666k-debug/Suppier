const sql = require('mssql');
require('dotenv').config();

const dbConfig = {
  user: process.env.DB_USER || 'sa',
  password: process.env.DB_PASSWORD || '',
  server: process.env.DB_SERVER || 'localhost',
  port: parseInt(process.env.DB_PORT || '1433', 10),
  database: process.env.DB_NAME || 'SuppierDB',
  options: {
    encrypt: false, // Set to true if using Azure
    trustServerCertificate: true // Change to true for local dev / self-signed certs
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
