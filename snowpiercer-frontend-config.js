// Configuration for Snowpiercer Frontend
// Frontend URL: https://snowpiercer-pi.vercel.app/
// Backend URL: https://snowpiercer-backend-1.onrender.com

export const BACKEND_CONFIG = {
  // Production URLs
  BACKEND_URL: 'https://snowpiercer-backend-1.onrender.com',
  API_BASE_URL: 'https://snowpiercer-backend-1.onrender.com/api',
  
  // API Endpoints (based on your VolumeBot interface)
  ENDPOINTS: {
    // Health & Status
    health: '/health',
    status: '/api/status',
    
    // Token & Market Data
    tokens: '/api/tokens',
    tokenInfo: '/api/tokens/{mint}', // Replace {mint} with token mint address
    
    // Trading & Volume
    quote: '/api/quote',
    swap: '/api/swap', 
    volume: '/api/volume',
    simulate: '/api/simulate',
    
    // Bot Operations (matching your frontend interface)
    startBot: '/api/bot/start',
    stopBot: '/api/bot/stop',
    botStatus: '/api/bot/status',
    
    // Configuration
    config: '/api/config',
    wallets: '/api/wallets'
  },
  
  // Request configuration
  TIMEOUT: 30000, // 30 seconds (Render free tier can be slow)
  RETRY_ATTEMPTS: 3,
  
  // Headers
  DEFAULT_HEADERS: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
};

// Helper function to build full URLs
export const buildApiUrl = (endpoint) => {
  return `${BACKEND_CONFIG.BACKEND_URL}${endpoint}`;
};

// API call helper with error handling
export const apiCall = async (endpoint, options = {}) => {
  const url = buildApiUrl(endpoint);
  
  const config = {
    method: 'GET',
    headers: BACKEND_CONFIG.DEFAULT_HEADERS,
    timeout: BACKEND_CONFIG.TIMEOUT,
    ...options
  };
  
  try {
    console.log(`API Call: ${config.method} ${url}`);
    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`API Success: ${url}`, data);
    return { success: true, data };
    
  } catch (error) {
    console.error(`API Error: ${url}`, error);
    return { success: false, error: error.message };
  }
};

// Test backend connectivity
export const testConnection = async () => {
  console.log('🔄 Testing backend connection...');
  
  const testEndpoints = [
    '/health',
    '/',
    '/api/tokens'
  ];
  
  for (const endpoint of testEndpoints) {
    const result = await apiCall(endpoint);
    if (result.success) {
      console.log(`✅ ${endpoint}: Connected successfully`);
      return true;
    } else {
      console.log(`❌ ${endpoint}: ${result.error}`);
    }
  }
  
  console.log('⚠️ Backend may be sleeping (Render free tier). Keep trying...');
  return false;
};

// Example usage for your VolumeBot frontend:
/*
import { BACKEND_CONFIG, apiCall, testConnection } from './snowpiercer-frontend-config.js';

// Test connection when app loads
testConnection();

// Get available tokens
const getTokens = async () => {
  const result = await apiCall(BACKEND_CONFIG.ENDPOINTS.tokens);
  if (result.success) {
    return result.data;
  }
  throw new Error(result.error);
};

// Start volume bot
const startBot = async (config) => {
  const result = await apiCall(BACKEND_CONFIG.ENDPOINTS.startBot, {
    method: 'POST',
    body: JSON.stringify(config)
  });
  return result;
};
*/