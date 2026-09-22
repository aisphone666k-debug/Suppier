const { connectDB, sql } = require('../config/db');

// Mock initial data matching the frontend GM1 - MA - PMA requisitions
let MOCK_REQUISITIONS = [
  {
    id: 1,
    no: 1,
    partName: 'Timing Belt T10-920 (High Tensile)',
    spec: 'Width 25mm, Pitch 10mm, Polyurethane',
    position: 'Main Conveyor Drive Unit A',
    makerName: 'Bando / Gates Unitta',
    qty: 2,
    unit: 'pcs',
    remark: 'Urgent for line stop repair',
    poRef: 'PO-2026-0881',
    isUrgent: true,
    machineModel: 'NC-Cut-01',
    machineMaker: 'Amada',
    serialNo: 'SN-99812-JP',
    acCode: 'AC-5001',
    vendor: 'Bando Chemical (Thailand)',
    unitPrice: 1450,
    currency: 'THB',
    crCode: 'CR-01',
    quotationNo: 'QT-2609-001',
    leadTime: '7 Days',
    status: 'PO Issued'
  },
  {
    id: 2,
    no: 2,
    partName: 'Linear Guide Block HGH25CA',
    spec: 'Standard C-load, 23x48x83mm',
    position: 'Slide Axis Z-1',
    makerName: 'THK / HIWIN',
    qty: 4,
    unit: 'pcs',
    remark: 'Quarterly overhaul maintenance',
    poRef: '',
    isUrgent: false,
    machineModel: 'MC-HighSpeed-V5',
    machineMaker: 'Makino',
    serialNo: 'MK-2021-042',
    acCode: 'AC-5002',
    vendor: 'HIWIN Precision Co., Ltd.',
    unitPrice: 2800,
    currency: 'THB',
    crCode: 'CR-02',
    quotationNo: 'QT-2609-004',
    leadTime: '14 Days',
    status: 'Approved'
  }
];

/**
 * Get all requisition items
 * GET /api/requisition/items
 */
exports.getAllItems = async (req, res) => {
  try {
    const pool = await connectDB();

    if (pool) {
      try {
        const result = await pool.request()
          .query('SELECT * FROM RequisitionItems ORDER BY ItemNo ASC');
        return res.json({
          success: true,
          data: result.recordset
        });
      } catch (dbErr) {
        console.warn('Database query failed, using fallback data:', dbErr.message);
      }
    }

    return res.json({
      success: true,
      data: MOCK_REQUISITIONS
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
  try {
    const newItem = {
      id: Date.now(),
      no: MOCK_REQUISITIONS.length + 1,
      partName: req.body.partName || 'New Spare Part',
      spec: req.body.spec || '',
      position: req.body.position || '',
      makerName: req.body.makerName || '',
      qty: req.body.qty || 1,
      unit: req.body.unit || 'pcs',
      remark: req.body.remark || '',
      isUrgent: !!req.body.isUrgent,
      machineModel: req.body.machineModel || '',
      machineMaker: req.body.machineMaker || '',
      serialNo: req.body.serialNo || '',
      acCode: req.body.acCode || '',
      vendor: req.body.vendor || '',
      unitPrice: req.body.unitPrice || null,
      currency: req.body.currency || 'THB',
      crCode: req.body.crCode || '',
      quotationNo: req.body.quotationNo || '',
      leadTime: req.body.leadTime || '',
      status: req.body.status || 'Waiting Quotation'
    };

    MOCK_REQUISITIONS.push(newItem);

    return res.status(201).json({
      success: true,
      message: 'บันทึกรายการขอซื้อสำเร็จ',
      data: newItem
    });
  } catch (error) {
    console.error('Error creating item:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to create item'
    });
  }
};

/**
 * Update a requisition item
 * PUT /api/requisition/items/:id
 */
exports.updateItem = async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    const index = MOCK_REQUISITIONS.findIndex(item => item.id === id);

    if (index === -1) {
      return res.status(404).json({
        success: false,
        message: 'ไม่พบรายการที่ต้องการแก้ไข'
      });
    }

    MOCK_REQUISITIONS[index] = {
      ...MOCK_REQUISITIONS[index],
      ...req.body
    };

    return res.json({
      success: true,
      message: 'อัปเดตข้อมูลสำเร็จ',
      data: MOCK_REQUISITIONS[index]
    });
  } catch (error) {
    console.error('Error updating item:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to update item'
    });
  }
};
