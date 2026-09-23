const { connectDB, sql } = require('../config/db');

async function clearDatabase() {
  const shouldReseed = process.argv.includes('--seed');
  const targetEmp = process.argv.find(arg => arg.startsWith('--emp='))?.split('=')[1];

  console.log('🧹 [Suppier Database Cleanup Script]');
  const pool = await connectDB();
  if (!pool) {
    console.error('❌ Cannot connect to SQL Server database.');
    process.exit(1);
  }

  try {
    const transaction = new sql.Transaction(pool);
    await transaction.begin();

    if (targetEmp) {
      // Clear data for a specific employee account
      console.log(`🗑️ Clearing data for employee account: "${targetEmp}"...`);
      await transaction.request()
        .input('empNo', sql.NVarChar(50), targetEmp)
        .query(`
          DELETE FROM RequisitionItems WHERE UPPER(EmpNo) = UPPER(@empNo);
          DELETE FROM Requisitions WHERE UPPER(EmpNo) = UPPER(@empNo);
        `);
      await transaction.commit();
      console.log(`✅ Data for employee "${targetEmp}" cleared successfully!`);
    } else {
      // Clear all requisition data
      console.log('🗑️ Clearing all data from [RequisitionItems] and [Requisitions]...');
      await transaction.request().query(`
        DELETE FROM RequisitionItems;
        DBCC CHECKIDENT ('RequisitionItems', RESEED, 0);
        DELETE FROM Requisitions;
      `);
      await transaction.commit();
      console.log('✅ All data in [RequisitionItems] and [Requisitions] cleared and ID reseeded to 0!');

      if (shouldReseed) {
        console.log('🌱 Re-seeding initial default data...');
        const { execSync } = require('child_process');
        execSync('node scripts/init-db.js', { stdio: 'inherit', cwd: __dirname + '/..' });
      }
    }

    process.exit(0);
  } catch (err) {
    console.error('❌ Error during cleanup:', err.message);
    process.exit(1);
  }
}

clearDatabase();
