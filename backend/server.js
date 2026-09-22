const express = require('express');
const cors = require('cors');
require('dotenv').config();

const { connectDB } = require('./config/db');
const authRoutes = require('./routes/auth.routes');
const requisitionRoutes = require('./routes/requisition.routes');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:4200',
  credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logger middleware to display interaction logs clearly in terminal
app.use((req, res, next) => {
  const start = Date.now();
  const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });
  console.log(`\n=========================================================`);
  console.log(`📡 [${timestamp}] API Request: ${req.method} ${req.originalUrl}`);
  if (req.body && Object.keys(req.body).length > 0) {
    console.log(`📦 Request Body:`, JSON.stringify(req.body));
  }

  res.on('finish', () => {
    const duration = Date.now() - start;
    const statusIcon = res.statusCode >= 400 ? '❌' : '✅';
    console.log(`${statusIcon} [${timestamp}] API Response: ${req.method} ${req.originalUrl} | Status: ${res.statusCode} | Time: ${duration}ms`);
    console.log(`=========================================================`);
  });

  next();
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'online',
    system: 'Suppier Requisition API Backend',
    timestamp: new Date().toISOString()
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/requisition', requisitionRoutes);

// Start server and initialize DB connection
app.listen(PORT, async () => {
  console.log(`🚀 [Server] Backend running on http://localhost:${PORT}`);
  await connectDB();
});
