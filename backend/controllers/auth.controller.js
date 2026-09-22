const { connectDB, sql } = require('../config/db');

// Mock fallback employees when DB is not yet migrated
const MOCK_EMPLOYEES = [
  { id: 'BPT01', name: 'นาย กิตติพงษ์ สว่างจิตต์', department: 'GM1 Engineering', role: 'Engineer' },
  { id: 'MA105', name: 'นางสาว ศิริพร พัฒนากุล', department: 'MA Maintenance', role: 'Staff' },
  { id: 'GM101', name: 'นาย สุรชัย ชัยวัฒน์', department: 'GM1 Production', role: 'Supervisor' },
  { id: 'PMA01', name: 'นาย วรพจน์ กิจเจริญ', department: 'PMA Planning', role: 'Manager' },
  { id: '12345', name: 'Demo Administrator', department: 'Procurement GM1', role: 'Admin' }
];

/**
 * Verify 5-digit employee ID
 * POST /api/auth/verify-employee
 */
exports.verifyEmployee = async (req, res) => {
  try {
    const { employeeId } = req.body;

    if (!employeeId || employeeId.length !== 5) {
      return res.status(400).json({
        success: false,
        message: 'กรุณาระบุรหัสพนักงาน 5 หลักให้ถูกต้อง'
      });
    }

    const code = employeeId.toUpperCase();
    const pool = await connectDB();

    // 1. If database pool is active, query SQL Server table
    if (pool) {
      try {
        const result = await pool.request()
          .input('code', sql.NVarChar(10), code)
          .query('SELECT EmployeeID, FullName, Department, Role, IsActive FROM Employees WHERE EmployeeID = @code AND IsActive = 1');

        if (result.recordset && result.recordset.length > 0) {
          const user = result.recordset[0];
          return res.json({
            success: true,
            message: 'เข้าสู่ระบบสำเร็จ',
            user: {
              employeeId: user.EmployeeID,
              fullName: user.FullName,
              department: user.Department,
              role: user.Role
            }
          });
        } else {
          return res.status(401).json({
            success: false,
            message: 'รหัสพนักงานไม่ถูกต้อง หรือถูกระงับการใช้งาน'
          });
        }
      } catch (dbErr) {
        console.error('SQL query error, falling back to mock check:', dbErr);
      }
    }

    // 2. Mock Fallback (when DB is not ready yet)
    const mockUser = MOCK_EMPLOYEES.find(e => e.id === code) || 
      (code.startsWith('BPT') || code.startsWith('MA') ? {
        id: code,
        name: `เจ้าหน้าที่รหัส ${code}`,
        department: 'Manufacturing Department',
        role: 'Employee'
      } : null);

    if (mockUser) {
      return res.json({
        success: true,
        message: 'เข้าสู่ระบบสำเร็จ (Dev Mode)',
        user: {
          employeeId: mockUser.id,
          fullName: mockUser.name,
          department: mockUser.department,
          role: mockUser.role
        }
      });
    } else {
      return res.status(401).json({
        success: false,
        message: 'รหัสพนักงานไม่ถูกต้อง'
      });
    }

  } catch (error) {
    console.error('Verify employee error:', error);
    return res.status(500).json({
      success: false,
      message: 'เกิดข้อผิดพลาดในการตรวจสอบข้อมูลพนักงาน'
    });
  }
};
