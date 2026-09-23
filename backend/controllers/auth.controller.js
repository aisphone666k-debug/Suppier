const { connectDB, sql } = require('../config/db');
const fs = require('fs');
const path = require('path');

// Helper to format/clean employee name (e.g. remove "MR.  ", "MISS  ", "MRS.  " and single-space)
function cleanEmployeeName(rawName) {
  if (!rawName) return '';
  return rawName
    .replace(/^(MR\.|MISS|MRS\.|MS\.)\s+/i, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// Section abbreviation mapping for factory sections
function getSectionAbbreviation(sectionName) {
  if (!sectionName) return '';
  const upper = sectionName.toUpperCase().trim();
  const map = {
    'MACHINE MAINTENANCE': 'M/M',
    'PRODUCTION CONTROL': 'P/C',
    'PRODUCTION CONTROL(PC)': 'P/C',
    'QUALITY CONTROL': 'Q/C',
    'QUALITY CONTROL(QC)': 'Q/C',
    'QUALITY CONTROL HDEV6': 'Q/C',
    'QUALITY ASSURANCE': 'Q/A',
    'QUALITY ASSURANCE(QA)': 'Q/A',
    'PURCHASE': 'P/H',
    'ENGINEER': 'ENG',
    'PROCESS ENGINEER': 'PE',
    'FIRST ARTICLE ENGINEER': 'FAE',
    'SUPPLIE QUALITY CONTROL': 'SQC',
    'MATERIAL CONTROL': 'M/C',
    'FINAL INSPECTION': 'F/I',
    'INPROCESS INSPECTION': 'I/I',
    'COST REDUCTION': 'C/R',
    'PRODUCTION IMPROVEMENT': 'P/I',
    'PRODUCTION DIRECTION': 'P/D',
    'GAUGE CONTROL': 'G/C',
    'GENERAL ADMIN': 'GA',
    'FACTORY CO-ORDINATION': 'FC',
    'ASSEMBLY': 'ASSY',
    'MACHINING': 'MC'
  };
  return map[upper] || sectionName;
}

// Thai name dictionary mapping for known employees
const THAI_NAME_MAP = {
  'TK212': 'เหนือฟ้า พงษ์พรหม',
  '6284B': 'รวิภาส เขียนอักษร',
  'X4770': 'ดนุพล สุทธิวัฒนกุล',
  'A3415': 'อรุณี จันทร์ฉาย'
};

// Optional CSV fallback loader in case DB connection is interrupted
function findEmployeeFromCsv(empCode) {
  try {
    const csvPath = path.resolve(__dirname, '../../../../Master_Employee.csv');
    if (!fs.existsSync(csvPath)) return null;
    const content = fs.readFileSync(csvPath, 'utf8');
    const lines = content.split('\n');
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const cols = line.split(',');
      if (cols.length >= 3 && cols[1].toUpperCase() === empCode) {
        return {
          User_Id: cols[0],
          Emp_No: cols[1],
          Name: cols[2],
          Profile_Picture_Url: cols[3] || '',
          Division_Id: cols[4] || '',
          Section_Id: cols[5] || '',
          Process_Id: cols[6] || ''
        };
      }
    }
  } catch (err) {
    console.error('CSV fallback read error:', err.message);
  }
  return null;
}

/**
 * Verify employee ID from [Suppier].[dbo].[Master_Employee]
 * POST /api/auth/verify-employee
 */
exports.verifyEmployee = async (req, res) => {
  const { employeeId } = req.body;
  const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });

  console.log(`\n┌──────────────────────────────────────────────────────────┐`);
  console.log(`│ 🔐 [AUTH VERIFICATION] Request Received at ${timestamp}      │`);
  console.log(`│ 👉 Target Employee ID: "${employeeId || ''}"             │`);
  console.log(`└──────────────────────────────────────────────────────────┘`);

  if (!employeeId || employeeId.trim().length < 4) {
    console.warn(`⚠️ [Auth Error] Invalid Employee ID format: "${employeeId}"`);
    return res.status(400).json({
      success: false,
      message: 'กรุณาระบุรหัสพนักงานให้ถูกต้อง (4-5 หลัก)'
    });
  }

  const code = employeeId.trim().toUpperCase();

  try {
    const pool = await connectDB();

    if (pool) {
      console.log(`🔎 [Database Query] Searching [Suppier].[dbo].[Master_Employee] for Emp_No = '${code}'...`);
      
      const query = `
        SELECT TOP 1
          e.User_Id,
          e.Emp_No,
          e.Name,
          e.Profile_Picture_Url,
          e.Division_Id,
          d.Division_Code,
          d.Division_Name,
          d.Division_Purchase,
          e.Section_Id,
          s.Section_Code,
          s.Section_Name,
          e.Process_Id,
          p.Process_Code,
          p.Process_Name,
          e.Position_Group,
          e.ShiftGroup_Code,
          e.Deleted_At
        FROM [dbo].[Master_Employee] e
        LEFT JOIN [dbo].[Master_Division] d ON e.Division_Id = d.Division_Id
        LEFT JOIN [dbo].[Master_Section] s ON e.Section_Id = s.Section_Id
        LEFT JOIN [dbo].[Master_Process] p ON e.Process_Id = p.Process_Id
        WHERE UPPER(LTRIM(RTRIM(e.Emp_No))) = @code
      `;

      const result = await pool.request()
        .input('code', sql.NVarChar(20), code)
        .query(query);

      if (result.recordset && result.recordset.length > 0) {
        const emp = result.recordset[0];
        const rawName = emp.Name ? emp.Name.replace(/\s+/g, ' ').trim() : '';
        const fullName = cleanEmployeeName(rawName);
        const thaiName = THAI_NAME_MAP[code] || '';
        const division = emp.Division_Purchase || emp.Division_Name || 'MA';
        const section = getSectionAbbreviation(emp.Section_Name);

        const rawPos = (emp.Position_Group || '').toUpperCase().trim();
        let positionGroup = 'STAFF';
        if (rawPos.startsWith('STAFF')) {
          positionGroup = 'STAFF';
        } else if (rawPos === 'OPT' || rawPos.includes('OPERAT')) {
          positionGroup = 'OPERATOR';
        } else if (rawPos === 'TECH' || rawPos.includes('TECHNIC')) {
          positionGroup = 'TECHNICIAN';
        } else if (rawPos.includes('TRAINEE')) {
          positionGroup = 'STUDENT TRAINEE';
        } else if (rawPos) {
          positionGroup = rawPos;
        }

        console.log(`✨ [Database Result] MATCH FOUND!`);
        console.log(`   ├─ 🆔 Emp_No:    ${emp.Emp_No}`);
        console.log(`   ├─ 👤 Name:      ${fullName} (Raw: "${rawName}" | Thai: "${thaiName}")`);
        console.log(`   ├─ 🏢 Division:  ${division} (${emp.Division_Name || '-'})`);
        console.log(`   ├─ 🔧 Section:   ${section} (${emp.Section_Name || '-'})`);
        console.log(`   ├─ ⚙️ Process:   ${emp.Process_Name || '-'}`);
        console.log(`   └─ 🖼️ Avatar:    ${emp.Profile_Picture_Url || 'None'}`);

        return res.json({
          success: true,
          message: 'เข้าสู่ระบบสำเร็จ',
          user: {
            empNo: emp.Emp_No.trim(),
            fullName: fullName,
            titleName: rawName,
            rawName: thaiName || rawName,
            thaiName: thaiName,
            division: division,
            divisionName: emp.Division_Name || emp.Division_Purchase || '',
            section: section,
            sectionName: emp.Section_Name || '',
            process: emp.Process_Name || '',
            positionGroup: positionGroup,
            shiftGroup: emp.ShiftGroup_Code || '',
            profilePictureUrl: emp.Profile_Picture_Url || '',
            deletedAt: emp.Deleted_At
          }
        });
      } else {
        console.warn(`❌ [Database Result] No employee found in dbo.Master_Employee with Emp_No: "${code}"`);
      }
    } else {
      console.warn(`⚠️ [Database Pool] Database pool not connected. Trying CSV fallback...`);
    }

    // CSV fallback if database query returned no record or pool failed
    const csvEmp = findEmployeeFromCsv(code);
    if (csvEmp) {
      const rawName = csvEmp.Name ? csvEmp.Name.replace(/\s+/g, ' ').trim() : '';
      const fullName = cleanEmployeeName(rawName);
      const thaiName = THAI_NAME_MAP[code] || '';
      console.log(`📄 [CSV Fallback] Found in Master_Employee.csv: ${code} - ${fullName}`);

      return res.json({
        success: true,
        message: 'เข้าสู่ระบบสำเร็จ (จาก CSV)',
        user: {
          empNo: csvEmp.Emp_No,
          fullName: fullName,
          titleName: rawName,
          rawName: thaiName || rawName,
          thaiName: thaiName,
          division: 'MA',
          divisionName: 'MECHANICAL ASS\'Y',
          section: 'M/M',
          sectionName: 'MACHINE MAINTENANCE',
          process: 'General',
          positionGroup: 'STAFF',
          shiftGroup: 'A',
          profilePictureUrl: csvEmp.Profile_Picture_Url || ''
        }
      });
    }

    console.warn(`🚫 [Auth Denied] Invalid Employee ID "${code}" - not found in any source.`);
    return res.status(401).json({
      success: false,
      message: `รหัสพนักงาน "${code}" ไม่ถูกต้อง หรือไม่พบข้อมูลใน Master_Employee`
    });

  } catch (error) {
    console.error(`💥 [Auth Exception] Error verifying employee "${code}":`, error);
    return res.status(500).json({
      success: false,
      message: 'เกิดข้อผิดพลาดภายในระบบในการตรวจสอบข้อมูลพนักงาน'
    });
  }
};
