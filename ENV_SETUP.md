# Environment Variables Setup Guide

## Quick Start

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values:**
   - Required: `SOLANA_RPC_URL` (use dedicated RPC for production)
   - Optional: API keys for DexTools, Birdeye
   - Recommended: Adjust bot configuration values

3. **Never commit `.env` to git!**

## Required Variables

### Solana Configuration
```env
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
```
**⚠️ Important:** For production, use a dedicated RPC endpoint:
- Helius: `https://mainnet.helius-rpc.com/?api-key=YOUR_KEY`
- QuickNode: `https://YOUR_ENDPOINT.solana-mainnet.quiknode.pro/YOUR_KEY`
- Alchemy: `https://solana-mainnet.g.alchemy.com/v2/YOUR_KEY`

### Jupiter API
```env
JUPITER_API_BASE_URL=https://quote-api.jup.ag/v6
```
No key required - Jupiter API is free.

## DexScreener Integration (REQUIRED for Trending)

DexScreener API is **free and requires no API key**:
```env
DEXSCREENER_API_URL=https://api.dexscreener.com/latest
```

The bot automatically:
- ✅ Fetches real-time DexScreener metrics
- ✅ Monitors trending status
- ✅ Optimizes trades for DexScreener algorithm
- ✅ Verifies when trending is achieved

## Optional API Keys

### DexTools (Recommended)
Get API key from: https://www.dextools.io/
```env
DEXTOOLS_API_KEY=your_key_here
```
Without key, bot uses web scraping (less reliable).

### Birdeye (Optional)
Get API key from: https://birdeye.so/
```env
BIRDEYE_API_KEY=your_key_here
```

## Bot Configuration

### Sub-Wallet Settings
```env
SUB_WALLET_FUNDING_SOL=0.025    # SOL per sub-wallet (0.02-0.05 recommended)
GAS_FEE_RESERVE_SOL=0.5         # Reserve for gas fees
USABLE_BALANCE_PERCENTAGE=70    # 70% for trading, 30% reserved
```

### DexScreener Optimization
```env
DEXSCREENER_TARGET_VOLUME_24H=50000      # $50k minimum for trending
DEXSCREENER_TARGET_TRANSACTIONS=100      # 100+ transactions
DEXSCREENER_OPTIMAL_TRADE_SIZE_USD=500   # $500 per trade (optimal)
DEXSCREENER_CHECK_INTERVAL=300           # Check every 5 minutes
```

## Production Checklist

- [ ] Use dedicated Solana RPC endpoint (not public RPC)
- [ ] Set `DEBUG=False`
- [ ] Configure proper `FRONTEND_URL`
- [ ] Set appropriate rate limits
- [ ] Use secure key management (never store private keys in .env)
- [ ] Monitor API rate limits
- [ ] Test on devnet first

## Environment-Specific Files

- `.env.example` - Template (safe to commit)
- `.env` - Your actual config (NEVER commit)
- `.env.local` - Local development overrides
- `.env.production` - Production-specific values

## Security Notes

1. **Never commit `.env` files**
2. **Rotate API keys regularly**
3. **Use environment variables in deployment platforms** (Render, Heroku, etc.)
4. **Never store wallet private keys in .env** - use secure key management
5. **Use different keys for dev/staging/prod**

## Getting API Keys

### DexTools API Key
1. Visit https://www.dextools.io/
2. Sign up / Log in
3. Navigate to API section
4. Generate API key
5. Add to `.env`: `DEXTOOLS_API_KEY=your_key`

### Birdeye API Key
1. Visit https://birdeye.so/
2. Sign up for account
3. Navigate to API dashboard
4. Generate API key
5. Add to `.env`: `BIRDEYE_API_KEY=your_key`

### Dedicated Solana RPC
**Helius (Recommended):**
1. Visit https://helius.dev/
2. Sign up for free tier
3. Create API key
4. Use: `SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY`

**QuickNode:**
1. Visit https://www.quicknode.com/
2. Create account
3. Create Solana endpoint
4. Copy RPC URL to `.env`

## Testing Your Configuration

After setting up `.env`, test with:
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('SOLANA_RPC_URL:', os.getenv('SOLANA_RPC_URL'))"
```

## Troubleshooting

**"No module named 'dotenv'"**
```bash
pip install python-dotenv
```

**"Invalid RPC URL"**
- Check your RPC endpoint is accessible
- Verify API key is correct
- Try public RPC first: `https://api.mainnet-beta.solana.com`

**"DexScreener API error"**
- DexScreener API is free, no key needed
- Check internet connection
- Verify `DEXSCREENER_API_URL` is correct

