const express = require('express');
const router = express.Router();
const requisitionController = require('../controllers/requisition.controller');

// GET /api/requisition/items
router.get('/items', requisitionController.getAllItems);

// POST /api/requisition/items
router.post('/items', requisitionController.createItem);

// PUT /api/requisition/items/:id
router.put('/items/:id', requisitionController.updateItem);

module.exports = router;
