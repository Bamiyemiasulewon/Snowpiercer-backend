# UPDATED FOR SMITHII LOGIC: Render Deployment Guide

## Snowpiercer Backend - Advanced Volume Bot with Trending Features

This guide covers deploying your Snowpiercer backend (enhanced with Smithii-like logic) to Render.

### Key Features Added

✅ **Sub-wallet Generation**: Generate 100-10,000 temporary Solana keypairs  
✅ **Trading Modes**: Boost, Bump, Advanced, and Trending modes  
✅ **MEV Protection**: Jito bundle support for Advanced mode  
✅ **Trending Integration**: DexScreener, DexTools, and Birdeye metrics  
✅ **Anti-Detection**: Gaussian delays, variable slippage, burst patterns  
✅ **Render Compatibility**: Fixed deployment issues with uvicorn

---

## Pre-Deployment Checklist

### 1. Required Files ✅
- `Procfile` - Web process command for Render
- `.python-version` - Python version specification (3.11.9)
- `requirements.txt` - Updated with pinned versions
- `.env.example` - Environment variables template

### 2. Fixed Render Issues ✅
- **py command not found**: Fixed by using `uvicorn main:app` in Procfile
- **Dependencies**: Pinned FastAPI==0.117.1, uvicorn==0.37.0, solana==0.36.7
- **Python Version**: Set to 3.11.9 for cryptography compatibility

---

## Render Deployment Steps

### Step 1: Create New Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New"** → **"Web Service"**
3. Connect your GitHub repository: `Bamiyemiasulewon/Snowpiercer-backend`
4. Configure the service:

```
Name: snowpiercer-backend
Environment: Python 3
Region: Oregon (US West) or your preferred region
Branch: main (or your deployment branch)
```

### Step 2: Configure Build Settings

#### Build Command:
```bash
pip install -r requirements.txt
```

#### Start Command:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Step 3: Environment Variables

Add these environment variables in Render dashboard:

#### Core Configuration
```env
PYTHON_VERSION=3.11.9
WEB_CONCURRENCY=2
HOST=0.0.0.0
DEBUG=false
```

#### API URLs
```env
FRONTEND_URL=https://snowpiercer-pi.vercel.app
BACKEND_URL=https://snowpiercer-backend-1.onrender.com
API_BASE_URL=https://snowpiercer-backend-1.onrender.com/api
```

#### Solana Configuration
```env
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_WS_URL=wss://api.mainnet-beta.solana.com
JUPITER_API_BASE_URL=https://quote-api.jup.ag/v6
```

#### Smithii Logic - Bot Configuration
```env
MAX_SUB_WALLETS=10000
MIN_SUB_WALLETS=100
SUB_WALLET_FUNDING_SOL=0.01
MAX_BOT_DURATION_HOURS=24
BOOST_MODE_MAX_FREQUENCY=2
BUMP_MODE_BUY_RATIO=0.7
```

#### Jito Configuration (Optional)
```env
JITO_ENDPOINT=https://mainnet.block-engine.jito.wtf
JITO_TIP_ACCOUNT=96gYZGLnJYVFmbjzopPSU2QiEV5fGqZNyN9nmNhvrZU5
JITO_MIN_TIP_LAMPORTS=10000
JITO_MAX_TIP_LAMPORTS=100000
```

#### Trending APIs (Optional - for enhanced metrics)
```env
DEXSCREENER_API_URL=https://api.dexscreener.com/latest
DEXTOOLS_API_KEY=your_dextools_api_key_here
BIRDEYE_API_KEY=your_birdeye_api_key_here
```

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start the service with uvicorn
   - Assign a public URL

---

## Post-Deployment

### 1. Verify Deployment

Test these endpoints once deployed:

```bash
# Health check
curl https://snowpiercer-backend-1.onrender.com/health

# API status
curl https://snowpiercer-backend-1.onrender.com/api/status

# Trending metrics (example)
curl https://snowpiercer-backend-1.onrender.com/api/get-trending-metrics/So11111111111111111111111111111111111111112
```

### 2. Update Frontend Configuration

Update your frontend's environment variables to point to the new backend:

```env
NEXT_PUBLIC_BACKEND_URL=https://snowpiercer-backend-1.onrender.com
NEXT_PUBLIC_API_BASE_URL=https://snowpiercer-backend-1.onrender.com/api
```

### 3. Test Smithii Logic Features

#### Test Bot Creation:
```bash
curl -X POST https://snowpiercer-backend-1.onrender.com/api/run-volume-bot \
  -H "Content-Type: application/json" \
  -d '{
    "user_wallet": "your_wallet_address",
    "token_mint": "target_token_mint",
    "mode": "boost",
    "num_makers": 500,
    "duration_hours": 2,
    "trade_size_sol": 0.05,
    "slippage_pct": 1.5
  }'
```

#### Test Trending Analysis:
```bash
curl https://snowpiercer-backend-1.onrender.com/api/get-trending-metrics/So11111111111111111111111111111111111111112?timeframe=24h
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Build Fails - "py: command not found"
**Solution**: ✅ Fixed by using `uvicorn main:app` instead of `py main.py`

#### 2. Import Errors
**Solution**: ✅ Dependencies pinned in requirements.txt

#### 3. Cryptography Issues
**Solution**: ✅ Python version set to 3.11.9

#### 4. Memory Issues
**Solution**: 
- Reduce `WEB_CONCURRENCY` to 1-2
- Consider upgrading Render plan for higher memory

#### 5. Startup Timeout
**Solution**:
- Check logs in Render dashboard
- Ensure all imports are working
- Verify environment variables are set

### Checking Logs

Access logs in Render Dashboard:
1. Go to your service
2. Click "Logs" tab  
3. Monitor for startup issues

---

## Monitoring and Scaling

### Health Monitoring

The backend includes comprehensive health endpoints:
- `/health` - Basic health check
- `/api/status` - Detailed service status
- `/api/quick-status` - Fast status for frontend

### Auto-Deploy

Render will automatically redeploy when you push to your main branch.

### Scaling

For production load:
1. Upgrade to Professional plan ($25/month)
2. Increase `WEB_CONCURRENCY` 
3. Consider horizontal scaling with multiple services

---

## Security Notes

### API Keys
- Store sensitive keys (DexTools, Birdeye) in Render environment variables
- Never commit API keys to your repository

### Rate Limiting
The backend includes rate limiting for production use.

### CORS Configuration
Pre-configured for your frontend domains. Update as needed.

---

## Next Steps

1. **Deploy to Render** using this guide
2. **Test all endpoints** with your frontend
3. **Monitor performance** and adjust configuration
4. **Scale as needed** based on usage

Your Snowpiercer backend is now ready for production with advanced Smithii-like volume bot capabilities! 🚀

---

## Support

- **Render Documentation**: https://render.com/docs
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Solana Web3.py**: https://github.com/michaelhly/solana-py