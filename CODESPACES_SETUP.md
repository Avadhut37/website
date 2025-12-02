# GitHub Codespaces Setup Guide

## 🌐 Network Configuration for Codespaces

When running in GitHub Codespaces, the application automatically detects the environment and configures the correct URLs.

## ✅ What's Configured

### Automatic Environment Detection

The frontend (`frontend/src/config/api.js`) automatically detects:
- **Local Development**: Uses `http://localhost:8000`
- **GitHub Codespaces**: Uses forwarded port URLs like `https://your-codespace-8000.app.github.dev`

### CORS Configuration

The backend allows all origins in DEBUG mode (which is enabled in Codespaces):
- Development: `allow_origins=["*"]`
- Production: Uses specific origins from `.env`

### Port Forwarding

Codespaces automatically forwards:
- **Backend**: Port 8000 → `https://your-codespace-8000.app.github.dev`
- **Frontend**: Port 5173 → `https://your-codespace-5173.app.github.dev`

## 🚀 Quick Start in Codespaces

1. **Open Codespace** (automatically done if you're reading this)

2. **Install Dependencies**:
   ```bash
   npm run install:all
   ```

3. **Start Development**:
   ```bash
   npm run dev
   ```

4. **Check Status**:
   ```bash
   npm run status
   ```

## 🔍 Troubleshooting Network Issues

### 1. Check Port Visibility

In Codespaces, ensure ports are public:

1. Open the **PORTS** tab in VS Code
2. Find ports **8000** and **5173**
3. Right-click and set **Port Visibility** to **Public**

### 2. Verify Connection

The app includes a connection status indicator (bottom-right):
- 🟢 **Green**: Backend connected
- 🔴 **Red**: Connection failed
- 🔵 **Blue**: Checking connection

Hover over the indicator to see connection details.

### 3. Check Backend Health

```bash
# Get your Codespace name
echo $CODESPACE_NAME

# Test backend directly
curl https://$CODESPACE_NAME-8000.app.github.dev/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "codespaces",
  "codespace": {
    "name": "your-codespace-name",
    "backend_url": "https://your-codespace-8000.app.github.dev",
    "frontend_url": "https://your-codespace-5173.app.github.dev"
  }
}
```

### 4. Check Frontend Connection

Open browser console (F12) and look for:
```
🌐 Codespaces detected - API URL: https://your-codespace-8000.app.github.dev
📤 API Request: POST /ai/preview
📥 API Response: 200 /ai/preview
```

### 5. Manual Port Configuration

If automatic detection fails, set environment variable:

```bash
# In frontend/.env or frontend/.env.local
VITE_API_URL=https://your-codespace-8000.app.github.dev
```

Then restart:
```bash
npm run dev
```

## 🔧 Environment Variables

### Backend (.env)
```bash
DEBUG=true                    # Enable debug mode (allows CORS *)
CORS_ORIGINS=*               # Accept all origins in dev
```

### Frontend (.env.local) - Optional
```bash
VITE_API_URL=https://your-codespace-8000.app.github.dev
```

## 📊 Port Configuration

| Service | Port | Codespaces URL Pattern |
|---------|------|------------------------|
| Backend | 8000 | `https://{codespace}-8000.app.github.dev` |
| Frontend | 5173 | `https://{codespace}-5173.app.github.dev` |

## 🐛 Common Issues

### Issue: "Network Error" or "ERR_CONNECTION_REFUSED"

**Solution**:
1. Check ports are **public** in PORTS tab
2. Verify backend is running: `curl localhost:8000/health`
3. Check connection status indicator in app
4. Restart services: `npm run dev`

### Issue: "CORS Error"

**Solution**:
1. Ensure `DEBUG=true` in `backend/.env`
2. Restart backend
3. Check backend logs for CORS configuration

### Issue: Frontend shows "Checking backend connection..."

**Solution**:
1. Backend might not be running
2. Check backend logs: `tail -f dev.log`
3. Verify backend health: `curl localhost:8000/health`

### Issue: Wrong API URL detected

**Solution**:
1. Check browser console for detected URL
2. Set manual override in `frontend/.env.local`:
   ```bash
   VITE_API_URL=https://your-actual-codespace-8000.app.github.dev
   ```
3. Restart frontend

## ✅ Verification Checklist

Run these commands to verify setup:

```bash
# 1. Check if services are running
npm run status

# 2. Check ports are forwarded
gh codespace ports

# 3. Test backend directly
curl localhost:8000/health

# 4. Check frontend build
cd frontend && npm run build

# 5. View logs
tail -f dev.log
```

## 🌟 Best Practices

1. **Always use `npm run dev`** - Starts both services correctly
2. **Keep ports public** - Required for Codespaces to work
3. **Check connection indicator** - Visual feedback in the app
4. **Use browser console** - See detailed connection logs
5. **Monitor backend logs** - Check for CORS or connection issues

## 📚 Additional Resources

- [GitHub Codespaces Docs](https://docs.github.com/en/codespaces)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)

## 🆘 Need Help?

If you're still experiencing issues:

1. Check the connection status indicator in the app (bottom-right)
2. Open browser console (F12) for detailed logs
3. Review backend logs: `tail -f dev.log`
4. Ensure ports 8000 and 5173 are set to **Public** in PORTS tab
5. Try restarting: `npm run dev`

---

**Status**: ✅ Codespaces support enabled and configured
