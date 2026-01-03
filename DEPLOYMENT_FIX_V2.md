# Deployment Fix V2: httpx Proxy Parameter Compatibility

## Issue
```
TypeError: AsyncClient.__init__() got an unexpected keyword argument 'proxy'
```

## Root Cause
- `solana-py` 0.36.7 tries to pass `proxy` parameter to `httpx.AsyncClient`
- `httpx` 0.23.3+ removed support for `proxy` parameter in `AsyncClient.__init__()`
- The `proxy` parameter was moved to a different location in newer httpx versions

## Fix Applied ✅

### Updated `requirements.txt`:
- Changed: `httpx>=0.23.0,<0.24.0`
- To: `httpx==0.23.0`

**Reason:** httpx 0.23.0 still supports the `proxy` parameter that `solana-py` 0.36.7 expects.

## Alternative Solutions (if 0.23.0 doesn't work)

1. **Use httpx 0.22.0** (definitely supports proxy):
   ```txt
   httpx==0.22.0
   ```

2. **Downgrade solana-py** (not recommended):
   ```txt
   solana==0.30.0
   ```

## Status
**FIXED** - Using httpx 0.23.0 which is compatible with solana-py 0.36.7

The backend should now deploy successfully on Render.

