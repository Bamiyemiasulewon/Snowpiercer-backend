# VolumeBot Backend

Professional Solana volume bot backend API built with FastAPI and Jupiter aggregator integration.

## Features

- 🚀 **FastAPI** with async support and automatic API documentation
- 🔄 **Jupiter Integration** for optimal swap routing and transaction preparation
- 📊 **Volume Simulation** with cost estimation and timing optimization
- 🔍 **Token Discovery** with popular token listings
- 🛡️ **Security** - No wallet keys stored, preparation of unsigned transactions only
- 📝 **Comprehensive Logging** and error handling
- 🌐 **CORS Support** for frontend integration
- ⚡ **Production Ready** with proper dependency management

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health check with service status

### Trading
- `POST /get-swap-quote` - Get swap quote and serialized transaction
  - Request: `{inputMint, outputMint, amount, slippageBps}`
  - Response: `{swapTransaction, inputAmount, outputAmount, priceImpact, marketInfos}`

### Token Management
- `GET /tokens` - Get list of popular tokens for frontend autocomplete

### Volume Simulation
- `POST /simulate-volume` - Simulate volume trading strategy
  - Request: `{tokenMint, numTrades, durationMinutes, tradeSizeSol, slippageBps}`
  - Response: `{estimatedVolume, estimatedFees, estimatedTime, averageDelay, priceImpact}`

## Quick Start

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. **Clone and setup**:
   ```bash
   git clone <your-repo>
   cd volumebot-backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   
   # Windows
   venv\\Scripts\\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   # Copy .env file and customize if needed
   cp .env .env.local
   ```

5. **Run the server**:
   ```bash
   python main.py
   ```

The server will start on `http://localhost:8000`

## Configuration

Environment variables in `.env`:

```bash
# Solana Configuration
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_NETWORK=mainnet-beta

# Jupiter Configuration  
JUPITER_API_BASE_URL=https://quote-api.jup.ag/v6

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# CORS Configuration
FRONTEND_URL=http://localhost:3000
```

## Development

### Project Structure

```
volumebot-backend/
├── main.py                 # FastAPI application entry point
├── models.py              # Pydantic models for request/response
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration
├── api/
│   ├── __init__.py
│   └── routes.py         # API route handlers
└── services/
    ├── __init__.py
    ├── jupiter.py        # Jupiter aggregator service
    └── volume_simulator.py # Volume simulation logic
```

### Running in Development Mode

```bash
# Enable debug mode and auto-reload
export DEBUG=true
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Usage Examples

### Get Swap Quote

```bash
curl -X POST "http://localhost:8000/get-swap-quote" \
  -H "Content-Type: application/json" \
  -d '{
    "inputMint": "So11111111111111111111111111111111111111112",
    "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "amount": 100000000,
    "slippageBps": 50
  }'
```

### Get Popular Tokens

```bash
curl -X GET "http://localhost:8000/tokens"
```

### Simulate Volume Strategy

```bash
curl -X POST "http://localhost:8000/simulate-volume" \
  -H "Content-Type: application/json" \
  -d '{
    "tokenMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "numTrades": 100,
    "durationMinutes": 60,
    "tradeSizeSol": 0.01,
    "slippageBps": 50
  }'
```

## Security Considerations

- ⚠️ **No Private Keys**: This backend never handles private keys or signs transactions
- 🔒 **Unsigned Transactions**: Only prepares unsigned transactions for frontend signing
- 🌐 **CORS Protection**: Configured for specific frontend origins
- 📝 **Input Validation**: Comprehensive request validation with Pydantic
- 🚫 **No Fund Custody**: Never holds or manages user funds

## Production Deployment

### Environment Setup

1. **Set production environment variables**
2. **Use production Solana RPC** (not public endpoints for high volume)
3. **Configure proper logging** and monitoring
4. **Set up reverse proxy** (nginx) for SSL/TLS
5. **Use process manager** (PM2, systemd, or Docker)

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

### Health Monitoring

The `/health` endpoint provides detailed service status for monitoring:

```json
{
  "status": "healthy",
  "services": {
    "jupiter": "healthy",
    "database": "not_applicable"
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and support:
- Create an issue in the GitHub repository
- Check the logs in `volumebot.log` for debugging
- Review the API documentation at `/docs`