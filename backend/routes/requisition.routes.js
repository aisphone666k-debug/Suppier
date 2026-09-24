const express = require('express');
const router = express.Router();
const requisitionController = require('../controllers/requisition.controller');

// Per-Account Requisition Route (Load or initialize document for specific employee account)
// GET /api/requisition/account/:empNo
router.get('/account/:empNo', requisitionController.getDocumentByAccount);

// All user quotation requests for Purchase section view
// GET /api/requisition/all-requests
router.get('/all-requests', requisitionController.getAllRequests);

// Document Header & All-in-one routes
// GET /api/requisition/document (default doc)
router.get('/document', requisitionController.getDocument);

// GET /api/requisition/document/:docNumber
router.get('/document/:docNumber', requisitionController.getDocument);

// PUT /api/requisition/document/:docNumber
router.put('/document/:docNumber', requisitionController.updateDocument);

// POST /api/requisition/save-all (Saves Header and all Items transactionally for the account)
router.post('/save-all', requisitionController.saveAll);

// Items CRUD routes
// GET /api/requisition/items
router.get('/items', requisitionController.getAllItems);

// POST /api/requisition/items
router.post('/items', requisitionController.createItem);

// PUT /api/requisition/items/:id
router.put('/items/:id', requisitionController.updateItem);

// DELETE /api/requisition/items/:id
router.delete('/items/:id', requisitionController.deleteItem);

module.exports = router;
