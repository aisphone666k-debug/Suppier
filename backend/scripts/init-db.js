const { connectDB, sql } = require('../config/db');

async function initializeDatabase() {
  console.log('🚀 Starting Database Initialization for Suppier Requisition System...');
  const pool = await connectDB();
  if (!pool) {
    console.error('❌ Cannot connect to SQL Server database.');
    process.exit(1);
  }

  try {
    const transaction = new sql.Transaction(pool);
    await transaction.begin();

    // 1. Create Requisitions table if it does not exist
    console.log('📦 Checking / Creating table [Requisitions]...');
    await transaction.request().query(`
      IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Requisitions')
      BEGIN
        CREATE TABLE Requisitions (
          DocNumber NVARCHAR(50) PRIMARY KEY,
          EmpNo NVARCHAR(50),
          DocDate NVARCHAR(50),
          Status NVARCHAR(100),
          RequestBy NVARCHAR(50),
          Division NVARCHAR(20),
          Section NVARCHAR(20),
          SectionName NVARCHAR(50),
          Priority NVARCHAR(50),
          PriorityReason NVARCHAR(255),
          OrderType NVARCHAR(100),
          OrderTypeDesc NVARCHAR(255),
          SendToPurchase NVARCHAR(255),
          CC NVARCHAR(255),
          ApprovalComment NVARCHAR(255),
          CreatedAt DATETIME DEFAULT GETDATE(),
          UpdatedAt DATETIME DEFAULT GETDATE()
        );
        PRINT 'Table [Requisitions] created successfully.';
      END
    `);

    // 2. Create RequisitionItems table if it does not exist
    console.log('📦 Checking / Creating table [RequisitionItems]...');
    await transaction.request().query(`
      IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RequisitionItems')
      BEGIN
        CREATE TABLE RequisitionItems (
          ID INT IDENTITY(1,1) PRIMARY KEY,
          DocNumber NVARCHAR(50) NOT NULL,
          EmpNo NVARCHAR(50),
          ItemNo INT NOT NULL,
          PartName NVARCHAR(100) NOT NULL,
          Spec NVARCHAR(MAX),
          Position NVARCHAR(100),
          MakerName NVARCHAR(50),
          Qty DECIMAL(10,2) DEFAULT 1,
          Unit NVARCHAR(20) DEFAULT 'PCS',
          PoRef NVARCHAR(50),
          Remark NVARCHAR(255),
          IsUrgent BIT DEFAULT 0,
          AttachmentsJson NVARCHAR(MAX),
          MachineModel NVARCHAR(255),
          MachineMaker NVARCHAR(100),
          SerialNo NVARCHAR(50),
          AcCode NVARCHAR(50),
          Vendor NVARCHAR(50),
          UnitPrice DECIMAL(18,2) NULL,
          Currency NVARCHAR(20) DEFAULT 'BT',
          CrCode NVARCHAR(50),
          QuotationNo NVARCHAR(50),
          QuotationPdf NVARCHAR(255),
          LeadTime NVARCHAR(50),
          AcCode2 NVARCHAR(50),
          Vendor2 NVARCHAR(50),
          UnitPrice2 DECIMAL(18,2) NULL,
          Currency2 NVARCHAR(20) DEFAULT 'BT',
          CrCode2 NVARCHAR(50),
          QuotationNo2 NVARCHAR(50),
          QuotationPdf2 NVARCHAR(255),
          LeadTime2 NVARCHAR(50),
          Status NVARCHAR(50) DEFAULT 'Waiting Quotation',
          CreatedAt DATETIME DEFAULT GETDATE(),
          UpdatedAt DATETIME DEFAULT GETDATE()
        );
        PRINT 'Table [RequisitionItems] created successfully.';
      END
    `);

    await transaction.commit();
    console.log('✅ Tables checked/created successfully.');

    // 3. Seed initial document if empty
    const docCheck = await pool.request().query(`SELECT COUNT(*) as count FROM Requisitions WHERE DocNumber = 'DOC-2026-0901-003'`);
    if (docCheck.recordset[0].count === 0) {
      console.log('🌱 Seeding initial Requisition Document: DOC-2026-0901-003...');
      await pool.request()
        .input('docNumber', sql.NVarChar(50), 'DOC-2026-0901-003')
        .input('docDate', sql.NVarChar(50), '06/08/2026 17:41')
        .input('status', sql.NVarChar(100), 'Waiting for purchase approve')
        .input('requestBy', sql.NVarChar(50), 'PEERAPAT BUASA')
        .input('division', sql.NVarChar(20), 'MA')
        .input('section', sql.NVarChar(20), 'P/H')
        .input('sectionName', sql.NVarChar(50), 'MACHINE MAINTENANCE')
        .input('priority', sql.NVarChar(50), 'NORMAL')
        .input('priorityReason', sql.NVarChar(255), 'SPARE PART FOR UDI SYSTEM')
        .input('orderType', sql.NVarChar(100), 'Spare Part M/C')
        .input('orderTypeDesc', sql.NVarChar(255), 'อะไหล่ ของเครื่องจักร (ถ้าไม่มีใช้เครื่องจักรทำงานไม่ได้)')
        .input('sendToPurchase', sql.NVarChar(255), 'NATTHANICHA SONTHIKESORN, PEERAPAT BUASA, TICHAGORN PROMJAREE, SIRITORN KUSOLEIAM, KUNLADA PANMAN, THEERARAT NANTHAWISIT, ANUSARA KUEADET, CHANTHANY THAI')
        .input('cc', sql.NVarChar(255), '-')
        .input('approvalComment', sql.NVarChar(255), '')
        .query(`
          INSERT INTO Requisitions (
            DocNumber, DocDate, Status, RequestBy, Division, Section, SectionName,
            Priority, PriorityReason, OrderType, OrderTypeDesc, SendToPurchase, CC, ApprovalComment
          ) VALUES (
            @docNumber, @docDate, @status, @requestBy, @division, @section, @sectionName,
            @priority, @priorityReason, @orderType, @orderTypeDesc, @sendToPurchase, @cc, @approvalComment
          )
        `);
      console.log('✅ Document DOC-2026-0901-003 seeded.');
    }

    // 4. Seed initial items if empty for this doc
    const itemsCheck = await pool.request().query(`SELECT COUNT(*) as count FROM RequisitionItems WHERE DocNumber = 'DOC-2026-0901-003'`);
    if (itemsCheck.recordset[0].count === 0) {
      console.log('🌱 Seeding initial 4 items for DOC-2026-0901-003...');
      const seedItems = [
        {
          docNumber: 'DOC-2026-0901-003',
          itemNo: 1,
          partName: 'CONNECT AXIS DEVEC',
          spec: 'ST8101300',
          position: '',
          makerName: 'FEDEX',
          qty: 5,
          unit: 'PCS',
          poRef: '2008819',
          remark: 'Ref.Last qtt for issue pr fitst(Q-NMB240901 )',
          isUrgent: 0,
          attachmentsJson: '[]',
          machineModel: 'HGM10152N\n/ PMM F-4\n/ BROKEN',
          machineMaker: 'BM16#34',
          serialNo: '1231',
          acCode: '6218-G',
          vendor: 'LNS',
          unitPrice: null,
          currency: 'BT',
          crCode: 'TX',
          quotationNo: '260902-150926-ST8101300.pdf',
          quotationPdf: '260902-150926-ST8101300.pdf',
          leadTime: '20-25 DAYS',
          acCode2: '',
          vendor2: '',
          unitPrice2: null,
          currency2: 'BT',
          crCode2: '',
          quotationNo2: '',
          quotationPdf2: '',
          leadTime2: '',
          status: 'Quoted'
        },
        {
          docNumber: 'DOC-2026-0901-003',
          itemNo: 2,
          partName: 'FILTER',
          spec: 'FOR CLEANVY\n(FVH4-3856V2CV)',
          position: '',
          makerName: 'CLEANVY',
          qty: 2,
          unit: 'PCS',
          poRef: '2108146/22222ZS',
          remark: 'Ref.Last qtt for issue pr fitsy',
          isUrgent: 0,
          attachmentsJson: JSON.stringify([{ name: '20250428140628.pdf', type: 'pdf', size: '1.2 MB' }]),
          machineModel: 'HGG11166N\n/ PMM F-1\n/ DIRTY',
          machineMaker: 'Cleanvy#02',
          serialNo: 'A06-026',
          acCode: '',
          vendor: 'IPO',
          unitPrice: null,
          currency: 'BT',
          crCode: '',
          quotationNo: 'WAIT',
          quotationPdf: '',
          leadTime: '',
          acCode2: '',
          vendor2: 'SIAM OHGITANI\n2108146',
          unitPrice2: null,
          currency2: 'BT',
          crCode2: '',
          quotationNo2: '',
          quotationPdf2: '',
          leadTime2: '',
          status: 'Waiting Quotation'
        },
        {
          docNumber: 'DOC-2026-0901-003',
          itemNo: 3,
          partName: 'DISTILLATION COIL',
          spec: 'COIL-200L\n(INSIDE)\n/FVH4-3856V2CV',
          position: '',
          makerName: 'CLEANVY',
          qty: 3,
          unit: 'PCS',
          poRef: '2108146/22222ZS\n(Ref.po:G33602A)',
          remark: 'Ref.Last price for issue pr first(27,000bt)\n(Q202410-002NMBT)',
          isUrgent: 1,
          attachmentsJson: '[]',
          machineModel: 'HGG12643N\n/ PMM F-1\n/ DEFECT',
          machineMaker: 'Cleanvy#02',
          serialNo: 'A06-026',
          acCode: '',
          vendor: 'IPO',
          unitPrice: null,
          currency: 'BT',
          crCode: '',
          quotationNo: 'WAIT',
          quotationPdf: '',
          leadTime: '',
          acCode2: '',
          vendor2: 'SIAM OHGITANI\n2108146',
          unitPrice2: null,
          currency2: 'BT',
          crCode2: '',
          quotationNo2: '',
          quotationPdf2: '',
          leadTime2: '',
          status: 'Waiting Quotation'
        },
        {
          docNumber: 'DOC-2026-0901-003',
          itemNo: 4,
          partName: 'DISTILLATION COIL',
          spec: 'COIL-200L\n(OUTSIDE)\n/FVH4-3856V2CV',
          position: '',
          makerName: 'CLEANVY',
          qty: 3,
          unit: 'PCS',
          poRef: '2108146/22222ZS\n(Ref.po:G33603A)',
          remark: 'Ref.Last price for issue',
          isUrgent: 1,
          attachmentsJson: '[]',
          machineModel: 'HGG12644N\n/ PMM F-1\n/ DEFECT',
          machineMaker: 'Cleanvy#02',
          serialNo: 'A06-026',
          acCode: '',
          vendor: 'IPO',
          unitPrice: null,
          currency: 'BT',
          crCode: '',
          quotationNo: 'WAIT',
          quotationPdf: '',
          leadTime: '',
          acCode2: '',
          vendor2: 'SIAM OHGITANI\n2108146',
          unitPrice2: null,
          currency2: 'BT',
          crCode2: '',
          quotationNo2: '',
          quotationPdf2: '',
          leadTime2: '',
          status: 'Waiting Quotation'
        }
      ];

      for (const item of seedItems) {
        await pool.request()
          .input('docNumber', sql.NVarChar(50), item.docNumber)
          .input('itemNo', sql.Int, item.itemNo)
          .input('partName', sql.NVarChar(100), item.partName)
          .input('spec', sql.NVarChar(sql.MAX), item.spec)
          .input('position', sql.NVarChar(100), item.position)
          .input('makerName', sql.NVarChar(50), item.makerName)
          .input('qty', sql.Decimal(10, 2), item.qty)
          .input('unit', sql.NVarChar(20), item.unit)
          .input('poRef', sql.NVarChar(50), item.poRef)
          .input('remark', sql.NVarChar(255), item.remark)
          .input('isUrgent', sql.Bit, item.isUrgent)
          .input('attachmentsJson', sql.NVarChar(sql.MAX), item.attachmentsJson)
          .input('machineModel', sql.NVarChar(255), item.machineModel)
          .input('machineMaker', sql.NVarChar(100), item.machineMaker)
          .input('serialNo', sql.NVarChar(50), item.serialNo)
          .input('acCode', sql.NVarChar(50), item.acCode)
          .input('vendor', sql.NVarChar(50), item.vendor)
          .input('unitPrice', sql.Decimal(18, 2), item.unitPrice)
          .input('currency', sql.NVarChar(20), item.currency)
          .input('crCode', sql.NVarChar(50), item.crCode)
          .input('quotationNo', sql.NVarChar(50), item.quotationNo)
          .input('quotationPdf', sql.NVarChar(255), item.quotationPdf)
          .input('leadTime', sql.NVarChar(50), item.leadTime)
          .input('acCode2', sql.NVarChar(50), item.acCode2)
          .input('vendor2', sql.NVarChar(50), item.vendor2)
          .input('unitPrice2', sql.Decimal(18, 2), item.unitPrice2)
          .input('currency2', sql.NVarChar(20), item.currency2)
          .input('crCode2', sql.NVarChar(50), item.crCode2)
          .input('quotationNo2', sql.NVarChar(50), item.quotationNo2)
          .input('quotationPdf2', sql.NVarChar(255), item.quotationPdf2)
          .input('leadTime2', sql.NVarChar(50), item.leadTime2)
          .input('status', sql.NVarChar(50), item.status)
          .query(`
            INSERT INTO RequisitionItems (
              DocNumber, ItemNo, PartName, Spec, Position, MakerName, Qty, Unit, PoRef, Remark,
              IsUrgent, AttachmentsJson, MachineModel, MachineMaker, SerialNo, AcCode, Vendor,
              UnitPrice, Currency, CrCode, QuotationNo, QuotationPdf, LeadTime,
              AcCode2, Vendor2, UnitPrice2, Currency2, CrCode2, QuotationNo2, QuotationPdf2, LeadTime2, Status
            ) VALUES (
              @docNumber, @itemNo, @partName, @spec, @position, @makerName, @qty, @unit, @poRef, @remark,
              @isUrgent, @attachmentsJson, @machineModel, @machineMaker, @serialNo, @acCode, @vendor,
              @unitPrice, @currency, @crCode, @quotationNo, @quotationPdf, @leadTime,
              @acCode2, @vendor2, @unitPrice2, @currency2, @crCode2, @quotationNo2, @quotationPdf2, @leadTime2, @status
            )
          `);
      }
      console.log('✅ Seeded 4 initial requisition items.');
    }

    console.log('🎉 Database initialization complete!');
    process.exit(0);
  } catch (err) {
    console.error('❌ Database Initialization Error:', err);
    process.exit(1);
  }
}

initializeDatabase();
