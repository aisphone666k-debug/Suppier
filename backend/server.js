const express = require('express');
const cors = require('cors');
require('dotenv').config();

const path = require('path');
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
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Serve static uploaded files (PDFs, images)
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Request logger middleware to display interaction logs clearly in terminal
app.use((req, res, next) => {
  const start = Date.now();
  const timestamp = new Date().toLocaleTimeString('th-TH', { hour12: false });
  console.log(`\n=========================================================`);
  console.log(`📡 [${timestamp}] API Request: ${req.method} ${req.originalUrl}`);
  if (req.body && Object.keys(req.body).length > 0) {
    if (req.originalUrl.includes('/upload') && req.body.fileData) {
      console.log(`📦 Request Body:`, JSON.stringify({ ...req.body, fileData: `[Base64 Data ${req.body.fileData.length} chars]` }));
    } else {
      const bodyStr = JSON.stringify(req.body);
      console.log(`📦 Request Body:`, bodyStr.length > 500 ? bodyStr.substring(0, 500) + '... (truncated)' : bodyStr);
    }
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
