# Deployment Fix: Solana Keypair Import

## Issue
```
ModuleNotFoundError: No module named 'solana.keypair'
```

## Root Cause
In newer versions of `solana-py` (0.36.7), the `Keypair` class has been moved from `solana.keypair` to `solders.keypair`.

## Fix Applied ✅

### Files Updated:
1. **`bot_logic.py`**
   - Changed: `from solana.keypair import Keypair`
   - To: `from solders.keypair import Keypair`

2. **`services/trade_executor.py`**
   - Changed: `from solana.keypair import Keypair`
   - To: `from solders.keypair import Keypair`

## Verification
- ✅ Syntax validation passed
- ✅ No linter errors
- ✅ All imports corrected

## Status
**FIXED** - Ready for deployment

The backend should now deploy successfully on Render.

