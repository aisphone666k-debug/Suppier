const express = require('express');
const router = express.Router();
const authController = require('../controllers/auth.controller');

// POST /api/auth/verify-employee
router.post('/verify-employee', authController.verifyEmployee);

module.exports = router;
