# VolumeBot Backend - Frontend Integration Guide

## Overview

This document provides comprehensive information for integrating with the VolumeBot backend API. The backend provides RESTful endpoints for volume trading simulation and execution, WebSocket support for real-time updates, wallet management, and comprehensive monitoring capabilities.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: Configure via `FRONTEND_URL` environment variable

## Authentication

Currently, the API uses public key-based wallet authentication. No API keys are required for basic operations, but wallet public keys are used for trade execution.

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Most endpoints: 30-60 requests per minute
- Execution endpoints: 5 requests per minute
- WebSocket connections are not rate limited

## API Endpoints

### 1. Health Check Endpoints

#### GET `/`
Basic health check.

**Response:**
```json
{
  "message": "VolumeBot backend ready"
}
```

#### GET `/health`
Detailed health check with service status.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "jupiter": "healthy",
    "database": "not_applicable"
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 2. Token Management

#### GET `/tokens`
Get list of supported tokens for trading.

**Response:**
```json
{
  "tokens": [
    {
      "mint": "So11111111111111111111111111111111111111112",
      "symbol": "SOL",
      "name": "Wrapped Solana",
      "decimals": 9,
      "logoURI": "https://..."
    }
  ],
  "count": 6
}
```

### 3. Swap Quotes

#### POST `/get-swap-quote`
Get swap quote and serialized transaction.

**Request Body:**
```json
{
  "inputMint": "So11111111111111111111111111111111111111112",
  "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "amount": 1000000000,
  "slippageBps": 50
}
```

**Response:**
```json
{
  "swapTransaction": "base64-encoded-transaction",
  "inputAmount": 1000000000,
  "outputAmount": 950000000,
  "priceImpact": 0.1,
  "marketInfos": []
}
```

### 4. Volume Simulation

#### POST `/simulate-volume`
Simulate volume trading strategy and get cost estimates.

**Request Body:**
```json
{
  "tokenMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "numTrades": 100,
  "durationMinutes": 60,
  "tradeSizeSol": 1.0,
  "slippageBps": 50
}
```

**Response:**
```json
{
  "estimatedVolume": 20000.0,
  "estimatedFees": 0.5,
  "estimatedTime": 60,
  "averageDelay": 36.0,
  "priceImpact": 0.15
}
```

### 5. Wallet Management

#### POST `/wallet/connect`
Connect and validate a wallet.

**Request Body:**
```json
{
  "publicKey": "wallet-public-key-here",
  "signature": "optional-signature-for-verification"
}
```

**Response:**
```json
{
  "publicKey": "wallet-public-key-here",
  "balance": 25.5,
  "connected": true,
  "lastUpdate": "2024-01-15T10:30:00.000Z"
}
```

#### GET `/wallet/{wallet_pubkey}/balance`
Get current wallet balance.

**Response:**
```json
{
  "publicKey": "wallet-public-key-here",
  "balance": 25.5,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 6. Trade Execution

#### POST `/execute/start`
Start a new volume trading execution.

**Request Body:**
```json
{
  "walletPublicKey": "wallet-public-key-here",
  "tokenMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "numTrades": 50,
  "durationMinutes": 30,
  "tradeSizeSol": 1.0,
  "slippageBps": 50,
  "strategy": "balanced"
}
```

**Response:**
```json
{
  "executionId": "uuid-here",
  "status": "pending",
  "message": "Volume trading execution started",
  "estimatedCompletionTime": "2024-01-15T11:00:00.000Z"
}
```

#### POST `/execute/{execution_id}/stop`
Stop an active execution.

**Response:**
```json
{
  "success": true,
  "message": "Execution stopped successfully",
  "executionId": "uuid-here"
}
```

#### GET `/execute/{execution_id}/status`
Get status of a specific execution.

**Response:**
```json
{
  "executionId": "uuid-here",
  "status": "running",
  "progress": 45.5,
  "tradesCompleted": 23,
  "totalTrades": 50,
  "volumeGenerated": 4600.0,
  "feesSpent": 0.23,
  "startTime": "2024-01-15T10:30:00.000Z",
  "lastUpdate": "2024-01-15T10:45:00.000Z"
}
```

#### GET `/execute/active`
Get all active executions.

**Response:**
```json
{
  "executions": {
    "uuid-1": {
      "id": "uuid-1",
      "status": "running",
      "trades_completed": 10,
      "start_time": "2024-01-15T10:30:00.000Z",
      "request": {}
    }
  },
  "count": 1
}
```

### 7. History and Monitoring

#### GET `/history/trades`
Get trade history with pagination.

**Query Parameters:**
- `execution_id` (optional): Filter by execution ID
- `page`: Page number (default: 1)
- `page_size`: Page size (default: 50, max: 200)

**Response:**
```json
{
  "trades": [
    {
      "executionId": "uuid-here",
      "timestamp": "2024-01-15T10:30:00.000Z",
      "tokenMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "tradeType": "buy",
      "amount": 1.0,
      "price": 100.0,
      "fees": 0.001,
      "status": "completed",
      "txSignature": "transaction-signature-here"
    }
  ],
  "total": 100,
  "page": 1,
  "pageSize": 50
}
```

#### GET `/history/executions`
Get execution history and summaries.

**Response:**
```json
{
  "executions": [
    {
      "executionId": "uuid-here",
      "walletPublicKey": "wallet-key-here",
      "tokenMint": "token-mint-here",
      "startTime": "2024-01-15T10:00:00.000Z",
      "endTime": "2024-01-15T11:00:00.000Z",
      "status": "completed",
      "tradesCompleted": 50,
      "totalVolume": 10000.0,
      "totalFees": 0.5,
      "efficiency": 98.5
    }
  ],
  "total": 10,
  "active": 2
}
```

#### GET `/stats`
Get system statistics.

**Response:**
```json
{
  "executions": {
    "active": 3,
    "total_completed": 25
  },
  "trades": {
    "total": 1250
  },
  "websockets": {
    "total_connections": 5,
    "execution_connections": 3,
    "global_connections": 2,
    "active_executions": 3
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## WebSocket Integration

### Connection Endpoints

#### Global WebSocket: `ws://localhost:8000/ws`
For general system updates and notifications.

#### Execution-specific WebSocket: `ws://localhost:8000/ws/{execution_id}`
For real-time updates about a specific trade execution.

### Message Format

All WebSocket messages follow this format:
```json
{
  "type": "message_type",
  "data": {},
  "timestamp": "2024-01-15T10:30:00.000Z",
  "executionId": "uuid-here"
}
```

### Message Types

#### `trade_update`
Real-time trade execution updates.
```json
{
  "type": "trade_update",
  "data": {
    "executionId": "uuid-here",
    "tradeNumber": 15,
    "totalTrades": 50,
    "status": "running",
    "volumeGenerated": 3000.0,
    "feesSpent": 0.15,
    "progress": 30.0,
    "lastTradeResult": {},
    "estimatedTimeRemaining": 20
  },
  "timestamp": "2024-01-15T10:30:00.000Z",
  "executionId": "uuid-here"
}
```

#### `status_update`
General status updates.
```json
{
  "type": "status_update",
  "data": {
    "status": "running",
    "message": "Execution proceeding normally"
  },
  "timestamp": "2024-01-15T10:30:00.000Z",
  "executionId": "uuid-here"
}
```

#### `error`
Error notifications.
```json
{
  "type": "error",
  "data": {
    "error": "Trade failed",
    "details": "Insufficient balance"
  },
  "timestamp": "2024-01-15T10:30:00.000Z",
  "executionId": "uuid-here"
}
```

#### `ping`/`pong`
Heartbeat messages for connection health.

## Frontend Integration Examples

### JavaScript/TypeScript Examples

#### Basic API Client Setup
```typescript
class VolumeBot {
  private baseUrl = 'http://localhost:8000';
  
  async getTokens() {
    const response = await fetch(`${this.baseUrl}/tokens`);
    return response.json();
  }
  
  async simulateVolume(params: VolumeSimulationRequest) {
    const response = await fetch(`${this.baseUrl}/simulate-volume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return response.json();
  }
  
  async startExecution(params: TradeExecutionRequest) {
    const response = await fetch(`${this.baseUrl}/execute/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return response.json();
  }
}
```

#### WebSocket Integration
```typescript
class WebSocketManager {
  private ws: WebSocket | null = null;
  
  connect(executionId?: string) {
    const wsUrl = executionId 
      ? `ws://localhost:8000/ws/${executionId}`
      : 'ws://localhost:8000/ws';
      
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      // Send ping periodically
      setInterval(() => {
        this.send({ type: 'ping' });
      }, 30000);
    };
  }
  
  private handleMessage(message: any) {
    switch (message.type) {
      case 'trade_update':
        this.onTradeUpdate(message.data);
        break;
      case 'status_update':
        this.onStatusUpdate(message.data);
        break;
      case 'error':
        this.onError(message.data);
        break;
    }
  }
  
  private send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}
```

### React Hook Example
```typescript
function useVolumeExecution(executionId: string) {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  
  useEffect(() => {
    const wsManager = new WebSocketManager();
    wsManager.connect(executionId);
    
    wsManager.onTradeUpdate = (data) => {
      setProgress(data.progress);
      setStatus(data.status);
    };
    
    return () => wsManager.disconnect();
  }, [executionId]);
  
  return { status, progress };
}
```

## Error Handling

The API uses standard HTTP status codes:
- `200`: Success
- `400`: Bad Request (validation errors)
- `404`: Not Found
- `429`: Too Many Requests (rate limited)
- `500`: Internal Server Error

Error responses follow this format:
```json
{
  "error": "Error message",
  "detail": "Additional details",
  "code": 400
}
```

## Environment Setup

1. Copy `.env.example` to `.env`
2. Configure environment variables:
   - `HOST`: Server host (default: 0.0.0.0)
   - `PORT`: Server port (default: 8000)
   - `FRONTEND_URL`: Your frontend URL
   - `JUPITER_API_BASE_URL`: Jupiter API endpoint
   - `DEBUG`: Enable debug mode

## Production Considerations

1. **Security**: Implement proper authentication
2. **Rate Limiting**: Configure appropriate limits
3. **Logging**: Enable file logging for production
4. **Monitoring**: Use the `/stats` endpoint for monitoring
5. **Error Handling**: Implement comprehensive error handling
6. **WebSocket Management**: Handle connection drops and reconnections

## Testing

Use the built-in FastAPI docs at `http://localhost:8000/docs` for interactive API testing.

## Support

For issues and questions, refer to the backend logs and check the `/health` endpoint for service status.