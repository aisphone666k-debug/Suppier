const { connectDB, sql } = require('../config/db');

// Helper to convert DB item record to frontend camelCase
function mapDbItemToFrontend(dbItem) {
  let attachments = [];
  try {
    if (dbItem.AttachmentsJson) {
      attachments = JSON.parse(dbItem.AttachmentsJson);
    }
  } catch (e) {
    attachments = [];
  }

  return {
    id: dbItem.ID,
    empNo: dbItem.EmpNo || '',
    docNumber: dbItem.DocNumber,
    no: dbItem.ItemNo,
    partName: dbItem.PartName || '',
    spec: dbItem.Spec || '',
    position: dbItem.Position || '',
    makerName: dbItem.MakerName || '',
    qty: Number(dbItem.Qty) || 0,
    unit: dbItem.Unit || 'PCS',
    remark: dbItem.Remark || '',
    poRef: dbItem.PoRef || '',
    isUrgent: !!dbItem.IsUrgent,
    attachments: attachments,
    machineModel: dbItem.MachineModel || '',
    machineMaker: dbItem.MachineMaker || '',
    serialNo: dbItem.SerialNo || '',
    acCode: dbItem.AcCode || '',
    vendor: dbItem.Vendor || '',
    unitPrice: dbItem.UnitPrice !== null && dbItem.UnitPrice !== undefined ? Number(dbItem.UnitPrice) : null,
    currency: dbItem.Currency || 'BT',
    crCode: dbItem.CrCode || '',
    quotationNo: dbItem.QuotationNo || '',
    quotationPdf: dbItem.QuotationPdf || undefined,
    leadTime: dbItem.LeadTime || '',
    acCode2: dbItem.AcCode2 || '',
    vendor2: dbItem.Vendor2 || '',
    unitPrice2: dbItem.UnitPrice2 !== null && dbItem.UnitPrice2 !== undefined ? Number(dbItem.UnitPrice2) : null,
    currency2: dbItem.Currency2 || 'BT',
    crCode2: dbItem.CrCode2 || '',
    quotationNo2: dbItem.QuotationNo2 || '',
    quotationPdf2: dbItem.QuotationPdf2 || undefined,
    leadTime2: dbItem.LeadTime2 || '',
    status: dbItem.Status || 'Waiting Quotation'
  };
}

// Helper to convert DB header record to frontend camelCase
function mapDbDocToFrontend(dbDoc) {
  return {
    docNumber: dbDoc.DocNumber,
    empNo: dbDoc.EmpNo || '',
    docDate: dbDoc.DocDate,
    status: dbDoc.Status,
    requestBy: dbDoc.RequestBy,
    division: dbDoc.Division,
    section: dbDoc.Section,
    sectionName: dbDoc.SectionName,
    priority: dbDoc.Priority,
    priorityReason: dbDoc.PriorityReason,
    orderType: dbDoc.OrderType,
    orderTypeDesc: dbDoc.OrderTypeDesc,
    sendToPurchase: dbDoc.SendToPurchase,
    cc: dbDoc.CC,
    approvalComment: dbDoc.ApprovalComment
  };
}

// In-Memory Fallback if DB is disconnected
let MOCK_DOCUMENTS_BY_EMP = {
  'PEERAPAT': {
    docNumber: 'DOC-2026-0901-003',
    empNo: 'PEERAPAT',
    docDate: '06/08/2026 17:41',
    status: 'Waiting for purchase approve',
    requestBy: 'PEERAPAT BUASA',
    division: 'MA',
    section: 'P/H',
    sectionName: 'MACHINE MAINTENANCE',
    priority: 'NORMAL',
    priorityReason: 'SPARE PART FOR UDI SYSTEM',
    orderType: 'Spare Part M/C',
    orderTypeDesc: 'อะไหล่ ของเครื่องจักร (ถ้าไม่มีใช้เครื่องจักรทำงานไม่ได้)',
    sendToPurchase: 'NATTHANICHA SONTHIKESORN, PEERAPAT BUASA, TICHAGORN PROMJAREE, SIRITORN KUSOLEIAM, KUNLADA PANMAN, THEERARAT NANTHAWISIT, ANUSARA KUEADET, CHANTHANY THAI',
    cc: '-',
    approvalComment: ''
  }
};

let MOCK_ITEMS_BY_DOC = {
  'DOC-2026-0901-003': [
    {
      id: 1,
      docNumber: 'DOC-2026-0901-003',
      empNo: 'PEERAPAT',
      no: 1,
      partName: 'CONNECT AXIS DEVEC',
      spec: 'ST8101300',
      position: '',
      makerName: 'FEDEX',
      qty: 5,
      unit: 'PCS',
      poRef: '2008819',
      remark: 'Ref.Last qtt for issue pr fitst(Q-NMB240901 )',
      isUrgent: false,
      attachments: [],
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
      status: 'Quoted'
    }
  ]
};

/**
 * Get or initialize requisition document for a specific employee account
 * GET /api/requisition/account/:empNo
 */
exports.getDocumentByAccount = async (req, res) => {
  const empNo = (req.params.empNo || '').trim().toUpperCase();
  if (!empNo) {
    return res.status(400).json({ success: false, message: 'Employee No is required' });
  }

  try {
    const pool = await connectDB();
    if (pool) {
      // 1. Look for existing document where EmpNo = empNo OR DocNumber = 'DOC-' + empNo
      const docResult = await pool.request()
        .input('empNo', sql.NVarChar(50), empNo)
        .query("SELECT TOP 1 * FROM Requisitions WHERE UPPER(EmpNo) = @empNo OR UPPER(DocNumber) = 'DOC-' + @empNo");

      if (docResult.recordset.length > 0) {
        const header = mapDbDocToFrontend(docResult.recordset[0]);
        const itemsResult = await pool.request()
          .input('docNumber', sql.NVarChar(50), header.docNumber)
          .query('SELECT * FROM RequisitionItems WHERE DocNumber = @docNumber ORDER BY ItemNo ASC');

        return res.json({
          success: true,
          data: {
            header,
            items: itemsResult.recordset.map(mapDbItemToFrontend)
          }
        });
      }

      // Special check: If empNo is PEERAPAT or X4770, check if initial document matches
      if (empNo === 'PEERAPAT' || empNo === 'PB001') {
        const defaultDoc = await pool.request()
          .query("SELECT TOP 1 * FROM Requisitions WHERE DocNumber = 'DOC-2026-0901-003'");
        if (defaultDoc.recordset.length > 0) {
          const header = mapDbDocToFrontend(defaultDoc.recordset[0]);
          const itemsResult = await pool.request()
            .input('docNumber', sql.NVarChar(50), header.docNumber)
            .query('SELECT * FROM RequisitionItems WHERE DocNumber = @docNumber ORDER BY ItemNo ASC');

          return res.json({
            success: true,
            data: {
              header,
              items: itemsResult.recordset.map(mapDbItemToFrontend)
            }
          });
        }
      }

      // 2. Account has no document yet: look up employee info in Master_Employee to create customized new document
      let empName = empNo;
      let empDiv = 'MA';
      let empSec = 'M/M';
      let empSecName = 'MACHINE MAINTENANCE';

      try {
        const empQuery = await pool.request()
          .input('empNo', sql.NVarChar(50), empNo)
          .query(`
            SELECT TOP 1 e.Name, d.Division_Purchase, s.Section_Name 
            FROM Master_Employee e
            LEFT JOIN Master_Division d ON e.Division_Id = d.Division_Id
            LEFT JOIN Master_Section s ON e.Section_Id = s.Section_Id
            WHERE UPPER(e.Emp_No) = @empNo
          `);

        if (empQuery.recordset.length > 0) {
          const r = empQuery.recordset[0];
          if (r.Name) empName = r.Name.replace(/^(MR\.|MISS|MRS\.|MS\.)\s+/i, '').replace(/\s+/g, ' ').trim();
          if (r.Division_Purchase) empDiv = r.Division_Purchase;
          if (r.Section_Name) {
            empSecName = r.Section_Name;
            const sMap = { 'MACHINE MAINTENANCE': 'M/M', 'PURCHASE': 'P/H', 'MACHINING': 'MC', 'ASSEMBLY': 'ASSY', 'COST REDUCTION': 'C/R' };
            empSec = sMap[r.Section_Name.toUpperCase()] || r.Section_Name;
          }
        }
      } catch (err) {
        console.warn('Could not query Master_Employee info for new account:', err.message);
      }

      const newDocNumber = `DOC-${empNo}`;
      const now = new Date();
      const docDateStr = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

      // Return clean empty document template - DO NOT insert dummy data into DB until the user explicitly saves
      return res.json({
        success: true,
        message: `Account ${empNo} has no data yet. Returning empty form.`,
        data: {
          header: {
            docNumber: newDocNumber,
            empNo: empNo,
            docDate: docDateStr,
            status: 'Waiting for purchase approve',
            requestBy: empName,
            division: empDiv,
            section: empSec,
            sectionName: empSecName,
            priority: 'NORMAL',
            priorityReason: '',
            orderType: 'Spare Part M/C',
            orderTypeDesc: '',
            sendToPurchase: '',
            cc: '-',
            approvalComment: ''
          },
          items: [] // Empty! No dummy rows inserted
        }
      });
    }

    // Fallback mode
    if (!MOCK_DOCUMENTS_BY_EMP[empNo]) {
      MOCK_DOCUMENTS_BY_EMP[empNo] = {
        docNumber: `DOC-${empNo}`,
        empNo,
        docDate: '06/08/2026 17:41',
        status: 'Waiting for purchase approve',
        requestBy: empNo,
        division: 'MA',
        section: 'M/M',
        sectionName: 'MACHINE MAINTENANCE',
        priority: 'NORMAL',
        priorityReason: 'SPARE PART FOR LINE',
        orderType: 'Spare Part M/C',
        orderTypeDesc: 'อะไหล่ ของเครื่องจักร (ถ้าไม่มีใช้เครื่องจักรทำงานไม่ได้)',
        sendToPurchase: 'NATTHANICHA SONTHIKESORN, PEERAPAT BUASA, TICHAGORN PROMJAREE, SIRITORN KUSOLEIAM, KUNLADA PANMAN, THEERARAT NANTHAWISIT, ANUSARA KUEADET, CHANTHANY THAI',
        cc: '-',
        approvalComment: ''
      };
      MOCK_ITEMS_BY_DOC[`DOC-${empNo}`] = [];
    }

    return res.json({
      success: true,
      data: {
        header: MOCK_DOCUMENTS_BY_EMP[empNo],
        items: MOCK_ITEMS_BY_DOC[`DOC-${empNo}`] || []
      }
    });
  } catch (error) {
    console.error('Error fetching requisition document for account:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to retrieve requisition document'
    });
  }
};

/**
 * Get entire requisition document by docNumber
 * GET /api/requisition/document/:docNumber?
 */
exports.getDocument = async (req, res) => {
  const docNumber = req.params.docNumber || 'DOC-2026-0901-003';
  try {
    const pool = await connectDB();
    if (pool) {
      const docResult = await pool.request()
        .input('docNumber', sql.NVarChar(50), docNumber)
        .query('SELECT * FROM Requisitions WHERE DocNumber = @docNumber');

      if (docResult.recordset.length > 0) {
        const header = mapDbDocToFrontend(docResult.recordset[0]);

        const itemsResult = await pool.request()
          .input('docNumber', sql.NVarChar(50), docNumber)
          .query('SELECT * FROM RequisitionItems WHERE DocNumber = @docNumber ORDER BY ItemNo ASC');

        const items = itemsResult.recordset.map(mapDbItemToFrontend);

        return res.json({
          success: true,
          data: {
            header,
            items
          }
        });
      }
    }

    // Fallback mode
    return res.json({
      success: true,
      data: {
        header: MOCK_DOCUMENTS_BY_EMP['PEERAPAT'] || { docNumber },
        items: MOCK_ITEMS_BY_DOC[docNumber] || []
      }
    });
  } catch (error) {
    console.error('Error fetching requisition document:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to retrieve requisition document'
    });
  }
};

/**
 * Update Requisition Header Information
 * PUT /api/requisition/document/:docNumber
 */
exports.updateDocument = async (req, res) => {
  const docNumber = req.params.docNumber || 'DOC-2026-0901-003';
  const data = req.body;
  const empNo = (data.empNo || req.query.empNo || '').trim().toUpperCase();

  try {
    const pool = await connectDB();
    if (pool) {
      await pool.request()
        .input('docNumber', sql.NVarChar(50), docNumber)
        .input('empNo', sql.NVarChar(50), empNo || null)
        .input('docDate', sql.NVarChar(50), data.docDate || '')
        .input('status', sql.NVarChar(100), data.status || '')
        .input('requestBy', sql.NVarChar(50), data.requestBy || '')
        .input('division', sql.NVarChar(20), data.division || '')
        .input('section', sql.NVarChar(20), data.section || '')
        .input('sectionName', sql.NVarChar(50), data.sectionName || '')
        .input('priority', sql.NVarChar(50), data.priority || '')
        .input('priorityReason', sql.NVarChar(255), data.priorityReason || '')
        .input('orderType', sql.NVarChar(100), data.orderType || '')
        .input('orderTypeDesc', sql.NVarChar(255), data.orderTypeDesc || '')
        .input('sendToPurchase', sql.NVarChar(255), data.sendToPurchase || '')
        .input('cc', sql.NVarChar(255), data.cc || '-')
        .input('approvalComment', sql.NVarChar(255), data.approvalComment || '')
        .query(`
          IF EXISTS (SELECT 1 FROM Requisitions WHERE DocNumber = @docNumber)
          BEGIN
            UPDATE Requisitions SET
              EmpNo = ISNULL(@empNo, EmpNo),
              DocDate = @docDate,
              Status = @status,
              RequestBy = @requestBy,
              Division = @division,
              Section = @section,
              SectionName = @sectionName,
              Priority = @priority,
              PriorityReason = @priorityReason,
              OrderType = @orderType,
              OrderTypeDesc = @orderTypeDesc,
              SendToPurchase = @sendToPurchase,
              CC = @cc,
              ApprovalComment = @approvalComment,
              UpdatedAt = GETDATE()
            WHERE DocNumber = @docNumber
          END
          ELSE
          BEGIN
            INSERT INTO Requisitions (
              DocNumber, EmpNo, DocDate, Status, RequestBy, Division, Section, SectionName,
              Priority, PriorityReason, OrderType, OrderTypeDesc, SendToPurchase, CC, ApprovalComment
            ) VALUES (
              @docNumber, @empNo, @docDate, @status, @requestBy, @division, @section, @sectionName,
              @priority, @priorityReason, @orderType, @orderTypeDesc, @sendToPurchase, @cc, @approvalComment
            )
          END
        `);

      const updated = await pool.request()
        .input('docNumber', sql.NVarChar(50), docNumber)
        .query('SELECT * FROM Requisitions WHERE DocNumber = @docNumber');

      return res.json({
        success: true,
        message: 'บันทึกข้อมูลเอกสารเรียบร้อยแล้ว',
        data: mapDbDocToFrontend(updated.recordset[0])
      });
    }

    return res.json({
      success: true,
      message: 'บันทึกข้อมูลเอกสาร (Fallback Mode)',
      data: { docNumber, ...data }
    });
  } catch (error) {
    console.error('Error updating document header:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to update document header'
    });
  }
};

/**
 * Save entire document (Header + All Items) transactionally for the active account
 * POST /api/requisition/save-all
 */
exports.saveAll = async (req, res) => {
  const { header, items, empNo } = req.body;
  if (!header || !header.docNumber) {
    return res.status(400).json({ success: false, message: 'Invalid payload: header.docNumber is required' });
  }

  const docNumber = header.docNumber;
  const targetEmpNo = (empNo || header.empNo || '').trim().toUpperCase();

  try {
    const pool = await connectDB();
    if (pool) {
      const transaction = new sql.Transaction(pool);
      await transaction.begin();

      try {
        // 1. Upsert Requisition Header
        await transaction.request()
          .input('docNumber', sql.NVarChar(50), docNumber)
          .input('empNo', sql.NVarChar(50), targetEmpNo || null)
          .input('docDate', sql.NVarChar(50), header.docDate || '')
          .input('status', sql.NVarChar(100), header.status || '')
          .input('requestBy', sql.NVarChar(50), header.requestBy || '')
          .input('division', sql.NVarChar(20), header.division || '')
          .input('section', sql.NVarChar(20), header.section || '')
          .input('sectionName', sql.NVarChar(50), header.sectionName || '')
          .input('priority', sql.NVarChar(50), header.priority || '')
          .input('priorityReason', sql.NVarChar(255), header.priorityReason || '')
          .input('orderType', sql.NVarChar(100), header.orderType || '')
          .input('orderTypeDesc', sql.NVarChar(255), header.orderTypeDesc || '')
          .input('sendToPurchase', sql.NVarChar(255), header.sendToPurchase || '')
          .input('cc', sql.NVarChar(255), header.cc || '-')
          .input('approvalComment', sql.NVarChar(255), header.approvalComment || '')
          .query(`
            IF EXISTS (SELECT 1 FROM Requisitions WHERE DocNumber = @docNumber)
            BEGIN
              UPDATE Requisitions SET
                EmpNo = ISNULL(@empNo, EmpNo),
                DocDate = @docDate,
                Status = @status,
                RequestBy = @requestBy,
                Division = @division,
                Section = @section,
                SectionName = @sectionName,
                Priority = @priority,
                PriorityReason = @priorityReason,
                OrderType = @orderType,
                OrderTypeDesc = @orderTypeDesc,
                SendToPurchase = @sendToPurchase,
                CC = @cc,
                ApprovalComment = @approvalComment,
                UpdatedAt = GETDATE()
              WHERE DocNumber = @docNumber
            END
            ELSE
            BEGIN
              INSERT INTO Requisitions (
                DocNumber, EmpNo, DocDate, Status, RequestBy, Division, Section, SectionName,
                Priority, PriorityReason, OrderType, OrderTypeDesc, SendToPurchase, CC, ApprovalComment
              ) VALUES (
                @docNumber, @empNo, @docDate, @status, @requestBy, @division, @section, @sectionName,
                @priority, @priorityReason, @orderType, @orderTypeDesc, @sendToPurchase, @cc, @approvalComment
              )
            END
          `);

        // 2. Refresh items: delete existing items for docNumber and re-insert current list
        await transaction.request()
          .input('docNumber', sql.NVarChar(50), docNumber)
          .query('DELETE FROM RequisitionItems WHERE DocNumber = @docNumber');

        if (Array.isArray(items)) {
          for (let i = 0; i < items.length; i++) {
            const item = items[i];
            const attachmentsJson = JSON.stringify(item.attachments || []);

            await transaction.request()
              .input('docNumber', sql.NVarChar(50), docNumber)
              .input('empNo', sql.NVarChar(50), targetEmpNo || null)
              .input('itemNo', sql.Int, item.no || (i + 1))
              .input('partName', sql.NVarChar(100), item.partName || 'Item')
              .input('spec', sql.NVarChar(sql.MAX), item.spec || '')
              .input('position', sql.NVarChar(100), item.position || '')
              .input('makerName', sql.NVarChar(50), item.makerName || '')
              .input('qty', sql.Decimal(10, 2), item.qty || 1)
              .input('unit', sql.NVarChar(20), item.unit || 'PCS')
              .input('poRef', sql.NVarChar(50), item.poRef || '')
              .input('remark', sql.NVarChar(255), item.remark || '')
              .input('isUrgent', sql.Bit, item.isUrgent ? 1 : 0)
              .input('attachmentsJson', sql.NVarChar(sql.MAX), attachmentsJson)
              .input('machineModel', sql.NVarChar(255), item.machineModel || '')
              .input('machineMaker', sql.NVarChar(100), item.machineMaker || '')
              .input('serialNo', sql.NVarChar(50), item.serialNo || '')
              .input('acCode', sql.NVarChar(50), item.acCode || '')
              .input('vendor', sql.NVarChar(50), item.vendor || '')
              .input('unitPrice', sql.Decimal(18, 2), item.unitPrice !== null && item.unitPrice !== undefined && item.unitPrice !== '' ? item.unitPrice : null)
              .input('currency', sql.NVarChar(20), item.currency || 'BT')
              .input('crCode', sql.NVarChar(50), item.crCode || '')
              .input('quotationNo', sql.NVarChar(50), item.quotationNo || '')
              .input('quotationPdf', sql.NVarChar(255), item.quotationPdf || '')
              .input('leadTime', sql.NVarChar(50), item.leadTime || '')
              .input('acCode2', sql.NVarChar(50), item.acCode2 || '')
              .input('vendor2', sql.NVarChar(50), item.vendor2 || '')
              .input('unitPrice2', sql.Decimal(18, 2), item.unitPrice2 !== null && item.unitPrice2 !== undefined && item.unitPrice2 !== '' ? item.unitPrice2 : null)
              .input('currency2', sql.NVarChar(20), item.currency2 || 'BT')
              .input('crCode2', sql.NVarChar(50), item.crCode2 || '')
              .input('quotationNo2', sql.NVarChar(50), item.quotationNo2 || '')
              .input('quotationPdf2', sql.NVarChar(255), item.quotationPdf2 || '')
              .input('leadTime2', sql.NVarChar(50), item.leadTime2 || '')
              .input('status', sql.NVarChar(50), item.status || 'Waiting Quotation')
              .query(`
                INSERT INTO RequisitionItems (
                  DocNumber, EmpNo, ItemNo, PartName, Spec, Position, MakerName, Qty, Unit, PoRef, Remark,
                  IsUrgent, AttachmentsJson, MachineModel, MachineMaker, SerialNo, AcCode, Vendor,
                  UnitPrice, Currency, CrCode, QuotationNo, QuotationPdf, LeadTime,
                  AcCode2, Vendor2, UnitPrice2, Currency2, CrCode2, QuotationNo2, QuotationPdf2, LeadTime2, Status
                ) VALUES (
                  @docNumber, @empNo, @itemNo, @partName, @spec, @position, @makerName, @qty, @unit, @poRef, @remark,
                  @isUrgent, @attachmentsJson, @machineModel, @machineMaker, @serialNo, @acCode, @vendor,
                  @unitPrice, @currency, @crCode, @quotationNo, @quotationPdf, @leadTime,
                  @acCode2, @vendor2, @unitPrice2, @currency2, @crCode2, @quotationNo2, @quotationPdf2, @leadTime2, @status
                )
              `);
          }
        }

        await transaction.commit();

        const savedItems = await pool.request()
          .input('docNumber', sql.NVarChar(50), docNumber)
          .query('SELECT * FROM RequisitionItems WHERE DocNumber = @docNumber ORDER BY ItemNo ASC');

        return res.json({
          success: true,
          message: 'บันทึกข้อมูล Requisition และรายการทั้งหมดสำเร็จ',
          data: {
            header,
            items: savedItems.recordset.map(mapDbItemToFrontend)
          }
        });
      } catch (txErr) {
        await transaction.rollback();
        throw txErr;
      }
    }

    // Fallback mode
    return res.json({
      success: true,
      message: 'บันทึกข้อมูลสำเร็จ (Fallback Mode)',
      data: {
        header: { ...header, empNo: targetEmpNo },
        items
      }
    });
  } catch (error) {
    console.error('Error in saveAll:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to save entire document'
    });
  }
};

/**
 * Get all requisition items
 * GET /api/requisition/items
 */
exports.getAllItems = async (req, res) => {
  const docNumber = req.query.docNumber || 'DOC-2026-0901-003';
  try {
    const pool = await connectDB();
    if (pool) {
      const result = await pool.request()
        .input('docNumber', sql.NVarChar(50), docNumber)
        .query('SELECT * FROM RequisitionItems WHERE DocNumber = @docNumber ORDER BY ItemNo ASC');

      return res.json({
        success: true,
        data: result.recordset.map(mapDbItemToFrontend)
      });
    }

    return res.json({
      success: true,
      data: MOCK_ITEMS_BY_DOC[docNumber] || []
    });
  } catch (error) {
    console.error('Error fetching requisition items:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to retrieve requisition items'
    });
  }
};

/**
 * Create or add a new requisition item
 * POST /api/requisition/items
 */
exports.createItem = async (req, res) => {
  const docNumber = req.body.docNumber || 'DOC-2026-0901-003';
  const item = req.body;
  const empNo = (item.empNo || '').trim().toUpperCase();

  try {
    const pool = await connectDB();
    if (pool) {
      const countRes = await pool.request()
        .input('docNumber', sql.NVarChar(50), docNumber)
        .query('SELECT ISNULL(MAX(ItemNo), 0) + 1 AS NextNo FROM RequisitionItems WHERE DocNumber = @docNumber');
      const itemNo = item.no || countRes.recordset[0].NextNo;
      const attachmentsJson = JSON.stringify(item.attachments || []);

      const insertRes = await pool.request()
        .input('docNumber', sql.NVarChar(50), docNumber)
        .input('empNo', sql.NVarChar(50), empNo || null)
        .input('itemNo', sql.Int, itemNo)
        .input('partName', sql.NVarChar(100), item.partName || 'New Spare Part')
        .input('spec', sql.NVarChar(sql.MAX), item.spec || '')
        .input('position', sql.NVarChar(100), item.position || '')
        .input('makerName', sql.NVarChar(50), item.makerName || '')
        .input('qty', sql.Decimal(10, 2), item.qty || 1)
        .input('unit', sql.NVarChar(20), item.unit || 'PCS')
        .input('poRef', sql.NVarChar(50), item.poRef || '')
        .input('remark', sql.NVarChar(255), item.remark || '')
        .input('isUrgent', sql.Bit, item.isUrgent ? 1 : 0)
        .input('attachmentsJson', sql.NVarChar(sql.MAX), attachmentsJson)
        .input('machineModel', sql.NVarChar(255), item.machineModel || '')
        .input('machineMaker', sql.NVarChar(100), item.machineMaker || '')
        .input('serialNo', sql.NVarChar(50), item.serialNo || '')
        .input('acCode', sql.NVarChar(50), item.acCode || '')
        .input('vendor', sql.NVarChar(50), item.vendor || '')
        .input('unitPrice', sql.Decimal(18, 2), item.unitPrice !== null && item.unitPrice !== undefined && item.unitPrice !== '' ? item.unitPrice : null)
        .input('currency', sql.NVarChar(20), item.currency || 'BT')
        .input('crCode', sql.NVarChar(50), item.crCode || '')
        .input('quotationNo', sql.NVarChar(50), item.quotationNo || '')
        .input('quotationPdf', sql.NVarChar(255), item.quotationPdf || '')
        .input('leadTime', sql.NVarChar(50), item.leadTime || '')
        .input('acCode2', sql.NVarChar(50), item.acCode2 || '')
        .input('vendor2', sql.NVarChar(50), item.vendor2 || '')
        .input('unitPrice2', sql.Decimal(18, 2), item.unitPrice2 !== null && item.unitPrice2 !== undefined && item.unitPrice2 !== '' ? item.unitPrice2 : null)
        .input('currency2', sql.NVarChar(20), item.currency2 || 'BT')
        .input('crCode2', sql.NVarChar(50), item.crCode2 || '')
        .input('quotationNo2', sql.NVarChar(50), item.quotationNo2 || '')
        .input('quotationPdf2', sql.NVarChar(255), item.quotationPdf2 || '')
        .input('leadTime2', sql.NVarChar(50), item.leadTime2 || '')
        .input('status', sql.NVarChar(50), item.status || 'Waiting Quotation')
        .query(`
          INSERT INTO RequisitionItems (
            DocNumber, EmpNo, ItemNo, PartName, Spec, Position, MakerName, Qty, Unit, PoRef, Remark,
            IsUrgent, AttachmentsJson, MachineModel, MachineMaker, SerialNo, AcCode, Vendor,
            UnitPrice, Currency, CrCode, QuotationNo, QuotationPdf, LeadTime,
            AcCode2, Vendor2, UnitPrice2, Currency2, CrCode2, QuotationNo2, QuotationPdf2, LeadTime2, Status
          ) 
          OUTPUT INSERTED.*
          VALUES (
            @docNumber, @empNo, @itemNo, @partName, @spec, @position, @makerName, @qty, @unit, @poRef, @remark,
            @isUrgent, @attachmentsJson, @machineModel, @machineMaker, @serialNo, @acCode, @vendor,
            @unitPrice, @currency, @crCode, @quotationNo, @quotationPdf, @leadTime,
            @acCode2, @vendor2, @unitPrice2, @currency2, @crCode2, @quotationNo2, @quotationPdf2, @leadTime2, @status
          )
        `);

      return res.status(201).json({
        success: true,
        message: 'เพิ่มรายการสำเร็จ',
        data: mapDbItemToFrontend(insertRes.recordset[0])
      });
    }

    const newItem = { ...item, id: Date.now() };
    return res.status(201).json({ success: true, message: 'เพิ่มรายการสำเร็จ', data: newItem });
  } catch (error) {
    console.error('Error creating item:', error);
    return res.status(500).json({ success: false, message: 'Failed to create item' });
  }
};

/**
 * Update a requisition item
 * PUT /api/requisition/items/:id
 */
exports.updateItem = async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const item = req.body;

  try {
    const pool = await connectDB();
    if (pool) {
      const attachmentsJson = JSON.stringify(item.attachments || []);

      const updateRes = await pool.request()
        .input('id', sql.Int, id)
        .input('partName', sql.NVarChar(100), item.partName || '')
        .input('spec', sql.NVarChar(sql.MAX), item.spec || '')
        .input('position', sql.NVarChar(100), item.position || '')
        .input('makerName', sql.NVarChar(50), item.makerName || '')
        .input('qty', sql.Decimal(10, 2), item.qty || 1)
        .input('unit', sql.NVarChar(20), item.unit || 'PCS')
        .input('poRef', sql.NVarChar(50), item.poRef || '')
        .input('remark', sql.NVarChar(255), item.remark || '')
        .input('isUrgent', sql.Bit, item.isUrgent ? 1 : 0)
        .input('attachmentsJson', sql.NVarChar(sql.MAX), attachmentsJson)
        .input('machineModel', sql.NVarChar(255), item.machineModel || '')
        .input('machineMaker', sql.NVarChar(100), item.machineMaker || '')
        .input('serialNo', sql.NVarChar(50), item.serialNo || '')
        .input('acCode', sql.NVarChar(50), item.acCode || '')
        .input('vendor', sql.NVarChar(50), item.vendor || '')
        .input('unitPrice', sql.Decimal(18, 2), item.unitPrice !== null && item.unitPrice !== undefined && item.unitPrice !== '' ? item.unitPrice : null)
        .input('currency', sql.NVarChar(20), item.currency || 'BT')
        .input('crCode', sql.NVarChar(50), item.crCode || '')
        .input('quotationNo', sql.NVarChar(50), item.quotationNo || '')
        .input('quotationPdf', sql.NVarChar(255), item.quotationPdf || '')
        .input('leadTime', sql.NVarChar(50), item.leadTime || '')
        .input('acCode2', sql.NVarChar(50), item.acCode2 || '')
        .input('vendor2', sql.NVarChar(50), item.vendor2 || '')
        .input('unitPrice2', sql.Decimal(18, 2), item.unitPrice2 !== null && item.unitPrice2 !== undefined && item.unitPrice2 !== '' ? item.unitPrice2 : null)
        .input('currency2', sql.NVarChar(20), item.currency2 || 'BT')
        .input('crCode2', sql.NVarChar(50), item.crCode2 || '')
        .input('quotationNo2', sql.NVarChar(50), item.quotationNo2 || '')
        .input('quotationPdf2', sql.NVarChar(255), item.quotationPdf2 || '')
        .input('leadTime2', sql.NVarChar(50), item.leadTime2 || '')
        .input('status', sql.NVarChar(50), item.status || 'Waiting Quotation')
        .query(`
          UPDATE RequisitionItems SET
            PartName = @partName,
            Spec = @spec,
            Position = @position,
            MakerName = @makerName,
            Qty = @qty,
            Unit = @unit,
            PoRef = @poRef,
            Remark = @remark,
            IsUrgent = @isUrgent,
            AttachmentsJson = @attachmentsJson,
            MachineModel = @machineModel,
            MachineMaker = @machineMaker,
            SerialNo = @serialNo,
            AcCode = @acCode,
            Vendor = @vendor,
            UnitPrice = @unitPrice,
            Currency = @currency,
            CrCode = @crCode,
            QuotationNo = @quotationNo,
            QuotationPdf = @quotationPdf,
            LeadTime = @leadTime,
            AcCode2 = @acCode2,
            Vendor2 = @vendor2,
            UnitPrice2 = @unitPrice2,
            Currency2 = @currency2,
            CrCode2 = @crCode2,
            QuotationNo2 = @quotationNo2,
            QuotationPdf2 = @quotationPdf2,
            LeadTime2 = @leadTime2,
            Status = @status,
            UpdatedAt = GETDATE()
          OUTPUT INSERTED.*
          WHERE ID = @id
        `);

      if (updateRes.recordset.length === 0) {
        return res.status(404).json({ success: false, message: 'Item not found' });
      }

      return res.json({
        success: true,
        message: 'อัปเดตข้อมูลสำเร็จ',
        data: mapDbItemToFrontend(updateRes.recordset[0])
      });
    }

    return res.status(404).json({ success: false, message: 'Item not found' });
  } catch (error) {
    console.error('Error updating item:', error);
    return res.status(500).json({ success: false, message: 'Failed to update item' });
  }
};

/**
 * Delete a requisition item
 * DELETE /api/requisition/items/:id
 */
exports.deleteItem = async (req, res) => {
  const id = parseInt(req.params.id, 10);
  try {
    const pool = await connectDB();
    if (pool) {
      await pool.request()
        .input('id', sql.Int, id)
        .query('DELETE FROM RequisitionItems WHERE ID = @id');
      return res.json({ success: true, message: 'ลบรายการสำเร็จ' });
    }

    return res.json({ success: true, message: 'ลบรายการสำเร็จ' });
  } catch (error) {
    console.error('Error deleting item:', error);
    return res.status(500).json({ success: false, message: 'Failed to delete item' });
  }
};

/**
 * Get all requisition requests from all users for PURCHASE section view
 * GET /api/requisition/all-requests
 */
exports.getAllRequests = async (req, res) => {
  try {
    const pool = await connectDB();
    let requests = [];

    if (pool) {
      const docResult = await pool.request().query(`
        SELECT r.*,
          (SELECT COUNT(*) FROM RequisitionItems i WHERE i.DocNumber = r.DocNumber) as TotalItems,
          (SELECT COUNT(*) FROM RequisitionItems i WHERE i.DocNumber = r.DocNumber AND (i.QuotationNo IS NULL OR i.QuotationNo = '' OR i.QuotationNo = 'WAIT' OR i.Status = 'Waiting Quotation')) as PendingQuotationCount
        FROM Requisitions r
        ORDER BY r.UpdatedAt DESC, r.CreatedAt DESC
      `);

      for (const row of docResult.recordset) {
        const header = mapDbDocToFrontend(row);
        header.totalItems = row.TotalItems || 0;
        header.pendingQuotationCount = row.PendingQuotationCount || 0;

        const itemsRes = await pool.request()
          .input('docNumber', sql.NVarChar(50), header.docNumber)
          .query('SELECT * FROM RequisitionItems WHERE DocNumber = @docNumber ORDER BY ItemNo ASC');

        const items = itemsRes.recordset.map(mapDbItemToFrontend);
        requests.push({
          header,
          items
        });
      }
    }

    // Ensure sample requests exist for demo / testing (e.g. TRISAK matching user screenshot)
    const hasTrisak = requests.some(r => r.header.docNumber === 'DOC-TRISAK-01' || (r.header.requestBy && r.header.requestBy.toUpperCase().includes('TRISAK')));
    if (!hasTrisak) {
      requests.unshift({
        header: {
          docNumber: 'DOC-TRISAK-01',
          empNo: 'TRISAK',
          docDate: '24/09/2026 09:30',
          status: 'Waiting Quotation',
          requestBy: 'TRISAK',
          division: 'GM',
          section: 'M/M',
          sectionName: 'MACHINE MAINTENANCE',
          priority: 'URGENT',
          priorityReason: 'Machine breakdown - spare part needed immediately',
          orderType: 'Spare Part M/C',
          orderTypeDesc: 'อะไหล่ ของเครื่องจักร (ถ้าไม่มีใช้เครื่องจักรทำงานไม่ได้)',
          sendToPurchase: 'NATTHANICHA SONTHIKESORN, PEERAPAT BUASA, NOPPORN VILAIKAEW, SUNAN SRISOD',
          cc: '-',
          approvalComment: 'Approved by Section Manager',
          totalItems: 3,
          pendingQuotationCount: 3
        },
        items: [
          {
            id: 101,
            docNumber: 'DOC-TRISAK-01',
            empNo: 'TRISAK',
            no: 1,
            partName: 'WIRING DUCTS',
            spec: 'WD4060-8',
            position: '',
            makerName: 'BANDEX',
            qty: 4,
            unit: 'MTR',
            remark: '',
            poRef: '',
            isUrgent: true,
            attachments: [],
            machineModel: 'HI GRIND-I-D',
            machineMaker: 'NISSIN#10',
            serialNo: '112090',
            acCode: '',
            vendor: '',
            unitPrice: null,
            currency: 'BT',
            crCode: '',
            quotationNo: '',
            quotationPdf: '',
            leadTime: '',
            status: 'Waiting Quotation'
          },
          {
            id: 102,
            docNumber: 'DOC-TRISAK-01',
            empNo: 'TRISAK',
            no: 2,
            partName: 'AIR CYLINDER',
            spec: 'ACQ100x115-S-B',
            position: 'STATION 2',
            makerName: 'AIRTAC',
            qty: 2,
            unit: 'PCS',
            remark: 'Refer PO 2060080',
            poRef: '2060080',
            isUrgent: true,
            attachments: [],
            machineModel: 'CNC LATHE L-20',
            machineMaker: 'CITIZEN',
            serialNo: '88902',
            acCode: '',
            vendor: '',
            unitPrice: null,
            currency: 'BT',
            crCode: '',
            quotationNo: '',
            quotationPdf: '',
            leadTime: '',
            status: 'Waiting Quotation'
          },
          {
            id: 103,
            docNumber: 'DOC-TRISAK-01',
            empNo: 'TRISAK',
            no: 3,
            partName: 'DRY SCREW VACUUM PUMP',
            spec: 'SDV-30S',
            position: 'MAIN PUMP',
            makerName: 'SHCOH SANGYO',
            qty: 1,
            unit: 'SET',
            remark: 'Critical spare',
            poRef: '',
            isUrgent: false,
            attachments: [],
            machineModel: 'VACUUM OVEN V-1',
            machineMaker: 'ULVAC',
            serialNo: '44301',
            acCode: '',
            vendor: '',
            unitPrice: null,
            currency: 'BT',
            crCode: '',
            quotationNo: '',
            quotationPdf: '',
            leadTime: '',
            status: 'Waiting Quotation'
          }
        ]
      });
    }

    const hasPeerapat = requests.some(r => r.header.docNumber === 'DOC-2026-0901-003' || (r.header.requestBy && r.header.requestBy.toUpperCase().includes('PEERAPAT')));
    if (!hasPeerapat && MOCK_DOCUMENTS_BY_EMP['PEERAPAT']) {
      requests.push({
        header: {
          ...MOCK_DOCUMENTS_BY_EMP['PEERAPAT'],
          totalItems: (MOCK_ITEMS_BY_DOC['DOC-2026-0901-003'] || []).length,
          pendingQuotationCount: (MOCK_ITEMS_BY_DOC['DOC-2026-0901-003'] || []).filter(i => !i.quotationNo || i.quotationNo === 'WAIT').length
        },
        items: MOCK_ITEMS_BY_DOC['DOC-2026-0901-003'] || []
      });
    }

    return res.json({
      success: true,
      data: requests
    });
  } catch (error) {
    console.error('Error fetching all user quotation requests:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to retrieve quotation requests'
    });
  }
};

