# 🚀 Suppier Backend API Service

ระบบ Backend API สำหรับเชื่อมต่อฐานข้อมูล (Database) ของระบบ **Request Quotation to Purchase (GM1 - MA - PMA)** และระบบยืนยันตัวตนด้วยรหัสพนักงาน 5 หลักสไตล์ OTP

---

## 📁 โครงสร้างโปรเจกต์ (Folder Structure)

```text
backend/
├── config/
│   └── db.js                       # จัดการการเชื่อมต่อฐานข้อมูล (SQL Server / Database Pooling)
├── controllers/
│   ├── auth.controller.js          # ตรวจสอบรหัสพนักงาน 5 หลัก และส่งข้อมูลผู้ใช้
│   └── requisition.controller.js   # ดึงข้อมูลและอัปเดตรายการใบขอซื้อ/เสนอราคา
├── routes/
│   ├── auth.routes.js              # เส้นทาง /api/auth/*
│   └── requisition.routes.js       # เส้นทาง /api/requisition/*
├── .env.example                    # ไฟล์ตัวอย่างตั้งค่า Environment & Database Connection
├── package.json                    # รายการไลบรารี Dependencies (Express, mssql, cors, dotenv)
├── server.js                       # จุดเริ่มต้น Express Server
└── README.md                       # คู่มือการใช้งาน
```

---

## ⚙️ วิธีการติดตั้งและเริ่มต้นใช้งาน (Installation & Setup)

1. **เข้าสู่โฟลเดอร์ backend:**
   ```bash
   cd backend
   ```

2. **ติดตั้ง Dependencies:**
   ```bash
   npm install
   ```

3. **ตั้งค่าฐานข้อมูล (.env):**
   คัดลอกไฟล์ `.env.example` ไปเป็น `.env`:
   ```bash
   cp .env.example .env
   ```
   จากนั้นแก้ไขข้อมูล Server, User, Password และ Database Name ให้ตรงกับฐานข้อมูลจริงของคุณ:
   ```env
   PORT=5000
   DB_SERVER=localhost
   DB_PORT=1433
   DB_USER=sa
   DB_PASSWORD=YourPassword123
   DB_NAME=SuppierDB
   ```

4. **รันเซิร์ฟเวอร์ Backend:**
   ```bash
   npm start
   # หรือสำหรับโหมดพัฒนา (Auto-reload)
   npm run dev
   ```

---

## 🗄️ ตัวอย่าง SQL Table Schema (สำหรับ SQL Server)

```sql
-- 1. ตารางพนักงาน (Employees)
CREATE TABLE Employees (
    EmployeeID NVARCHAR(10) PRIMARY KEY, -- เช่น 'BPT01', 'MA105'
    FullName NVARCHAR(150) NOT NULL,
    Department NVARCHAR(100) NOT NULL,
    Role NVARCHAR(50) DEFAULT 'Staff',
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE()
);

-- เพิ่มข้อมูลตัวอย่าง
INSERT INTO Employees (EmployeeID, FullName, Department, Role) VALUES
('BPT01', N'นาย กิตติพงษ์ สว่างจิตต์', N'GM1 Engineering', N'Engineer'),
('MA105', N'นางสาว ศิริพร พัฒนากุล', N'MA Maintenance', N'Staff'),
('GM101', N'นาย สุรชัย ชัยวัฒน์', N'GM1 Production', N'Supervisor');

-- 2. ตารางรายการขอซื้อ (RequisitionItems)
CREATE TABLE RequisitionItems (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    ItemNo INT NOT NULL,
    PartName NVARCHAR(255) NOT NULL,
    Spec NVARCHAR(255),
    Position NVARCHAR(255),
    MakerName NVARCHAR(150),
    Qty INT DEFAULT 1,
    Unit NVARCHAR(50) DEFAULT 'pcs',
    Remark NVARCHAR(500),
    IsUrgent BIT DEFAULT 0,
    MachineModel NVARCHAR(100),
    MachineMaker NVARCHAR(100),
    SerialNo NVARCHAR(100),
    AcCode NVARCHAR(50),
    Vendor NVARCHAR(150),
    UnitPrice DECIMAL(18,2),
    Currency NVARCHAR(10) DEFAULT 'THB',
    CrCode NVARCHAR(50),
    QuotationNo NVARCHAR(100),
    LeadTime NVARCHAR(50),
    Status NVARCHAR(50) DEFAULT 'Waiting Quotation',
    CreatedAt DATETIME DEFAULT GETDATE()
);
```

---

## 📡 รายการ API Endpoints

| Method | Endpoint | รายละเอียด |
| :--- | :--- | :--- |
| `GET` | `/api/health` | ตรวจสอบสถานะการทำงานของ Backend |
| `POST` | `/api/auth/verify-employee` | ตรวจสอบรหัสพนักงาน 5 หลัก (Body: `{ "employeeId": "BPT01" }`) |
| `GET` | `/api/requisition/items` | ดึงข้อมูลรายการขอซื้อทั้งหมด |
| `POST` | `/api/requisition/items` | เพิ่มรายการขอซื้อใหม่ |
| `PUT` | `/api/requisition/items/:id` | อัปเดตข้อมูลรายการขอซื้อตาม ID |
