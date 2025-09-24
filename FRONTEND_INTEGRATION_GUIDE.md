# 🔗 Frontend Integration Guide

## Backend URL
**Production Backend**: `https://snowpiercer-backend-1.onrender.com`

## API Endpoints

### Base URLs
- **API Base**: `https://snowpiercer-backend-1.onrender.com/api`
- **Documentation**: `https://snowpiercer-backend-1.onrender.com/docs`
- **Health Check**: `https://snowpiercer-backend-1.onrender.com/health`

### Key Endpoints
```javascript
const API_BASE = 'https://snowpiercer-backend-1.onrender.com/api';

// Available endpoints:
const endpoints = {
  tokens: `${API_BASE}/tokens`,           // Get available tokens
  quote: `${API_BASE}/quote`,             // Get swap quotes  
  swap: `${API_BASE}/swap`,               // Execute swaps
  volume: `${API_BASE}/volume`,           // Volume operations
  simulate: `${API_BASE}/simulate`,       // Simulate trades
  status: `${API_BASE}/status`,           // Get bot status
  health: 'https://snowpiercer-backend-1.onrender.com/health'
};
```

## Frontend Configuration

### Next.js Example
```javascript
// config/api.js
export const API_CONFIG = {
  baseURL: 'https://snowpiercer-backend-1.onrender.com',
  apiURL: 'https://snowpiercer-backend-1.onrender.com/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
};

// Example API call
async function fetchTokens() {
  const response = await fetch(`${API_CONFIG.apiURL}/tokens`);
  return response.json();
}
```

### React Example  
```javascript
// hooks/useAPI.js
const API_BASE = 'https://snowpiercer-backend-1.onrender.com/api';

export const useAPI = () => {
  const callAPI = async (endpoint, options = {}) => {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    return response.json();
  };

  return { callAPI };
};
```

## CORS Configuration
Your backend is configured to accept requests from:
- `https://snowpiercer-pi.vercel.app` ✅ **YOUR FRONTEND**
- `http://localhost:3000` (development)
- `https://volumebot-frontend.vercel.app`
- `https://snowpiercer-frontend.vercel.app`
- `https://snowpiercer-frontend.netlify.app`

## Environment Variables for Frontend

```bash
# .env.local (Next.js)
NEXT_PUBLIC_API_URL=https://snowpiercer-backend-1.onrender.com/api
NEXT_PUBLIC_BACKEND_URL=https://snowpiercer-backend-1.onrender.com

# .env (React/Vue)
REACT_APP_API_URL=https://snowpiercer-backend-1.onrender.com/api
REACT_APP_BACKEND_URL=https://snowpiercer-backend-1.onrender.com
```

## Testing the Connection

### Quick Test
```javascript
// Test backend connectivity
async function testConnection() {
  try {
    const response = await fetch('https://snowpiercer-backend-1.onrender.com/health');
    const data = await response.json();
    console.log('Backend status:', data.status);
    return data.status === 'healthy';
  } catch (error) {
    console.error('Backend connection failed:', error);
    return false;
  }
}
```

### API Documentation
Visit: `https://snowpiercer-backend-1.onrender.com/docs` for interactive API documentation.

## WebSocket (if implemented)
```javascript
const ws = new WebSocket('wss://snowpiercer-backend-1.onrender.com/ws');
```

## Common Issues & Solutions

1. **CORS Errors**: Make sure your frontend domain is added to the CORS configuration
2. **Timeout Issues**: Backend might be sleeping (Render free tier). First request may take 30+ seconds
3. **Rate Limiting**: Respect rate limits to avoid being blocked

## Support
- Backend logs available in Render dashboard
- API documentation: `/docs`
- Health check: `/health`