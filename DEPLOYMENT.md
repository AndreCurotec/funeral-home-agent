# Deployment Guide - Frontend to Netlify, Backend to Render

This guide will help you deploy the Funeral Home Chatbot with the frontend on Netlify and backend on Render, while maintaining local development compatibility.

## Architecture
- **Frontend**: Static files (HTML/CSS/JS) → Netlify
- **Backend**: FastAPI Python application → Render  
- **Auto-detection**: Works locally and in production automatically

## Step-by-Step Deployment

### 1. Deploy Backend to Render

#### 1.1 Prepare Repository
```bash
cd eazewell-agent
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

#### 1.2 Deploy to Render
1. Go to [render.com](https://render.com) → Sign up/Login
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `eazewell-agent-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Auto-Deploy**: Yes

#### 1.3 Set Environment Variables in Render
Go to Environment tab and add:
- `ENVIRONMENT` = `production`
- `OPENAI_API_KEY` = `your_openai_api_key`
- `FRONTEND_URL` = `https://your-netlify-app.netlify.app` (add after step 2)

#### 1.4 Note Your Render URL
After deployment: `https://your-app-name.onrender.com`

### 2. Deploy Frontend to Netlify

#### 2.1 Update Configuration
Edit `deploy-static/deploy-config.js`:
```javascript
const DEPLOYMENT_CONFIG = {
    // Replace with your actual Render URL from step 1.4
    BACKEND_URL: 'https://your-render-app-name.onrender.com',
    
    // Will be updated after Netlify deployment
    FRONTEND_URL: 'https://your-netlify-app-name.netlify.app'
};
```

#### 2.2 Deploy to Netlify
**Option A: Drag & Drop (Easiest)**
1. Go to [netlify.com](https://netlify.com) → Login
2. Drag the `deploy-static` folder to Netlify deployment area

**Option B: Git Integration (Recommended)**
1. Create new repository for frontend or use subfolder
2. Netlify → "New site from Git"
3. Configure:
   - **Base directory**: `deploy-static`
   - **Build command**: (leave empty)
   - **Publish directory**: `deploy-static`

#### 2.3 Note Your Netlify URL
After deployment: `https://wonderful-app-123.netlify.app`

### 3. Update URLs and Redeploy

#### 3.1 Update Backend CORS
In Render environment variables, set:
- `FRONTEND_URL` = `https://your-actual-netlify-url.netlify.app`

#### 3.2 Update Frontend Config
Edit `deploy-static/deploy-config.js` with actual URLs:
```javascript
const DEPLOYMENT_CONFIG = {
    BACKEND_URL: 'https://your-actual-render-app.onrender.com',
    FRONTEND_URL: 'https://your-actual-netlify-app.netlify.app'
};
```

#### 3.3 Redeploy Frontend
- If using drag & drop: Re-upload the `deploy-static` folder
- If using Git: Commit and push changes

## Local Development

### Running Locally
```bash
cd eazewell-agent
pip install -r requirements.txt
uvicorn main:app --reload
```

Access at: `http://localhost:8000`

### How It Works Locally
- Frontend served by FastAPI at `/` 
- API calls use relative paths (`/chat`)
- CORS allows localhost origins
- Configuration automatically detects local environment

## How Auto-Detection Works

### Frontend Logic (`deploy-config.js`)
```javascript
function getApiBaseUrl() {
    const isLocal = window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1';
    
    return isLocal ? '' : DEPLOYMENT_CONFIG.BACKEND_URL;
}
```

### Backend Logic (`main.py`)
```python
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    cors_origins = ["https://*.netlify.app", FRONTEND_URL]
else:
    cors_origins = ["*"]  # Allow all in development
```

## Testing Deployment

1. **Test Backend**: Visit `https://your-render-app.onrender.com/docs`
2. **Test Frontend**: Visit `https://your-netlify-app.netlify.app`
3. **Test Chat**: Send a message in the chat interface
4. **Check Console**: Look for CORS or API errors in browser dev tools

## URLs Summary
- **Local Development**: `http://localhost:8000`
- **Production Frontend**: `https://your-netlify-app.netlify.app`
- **Production Backend**: `https://your-render-app.onrender.com`
- **API Endpoint**: `https://your-render-app.onrender.com/chat`

## Troubleshooting

### Common Issues
1. **CORS Errors**: Check `FRONTEND_URL` environment variable in Render
2. **API Not Found**: Verify backend URL in `deploy-config.js`
3. **Cold Starts**: Render free tier has 15-30s delays after inactivity
4. **Local Not Working**: Ensure both files use same static folder

### Environment Variables Checklist
**Render Backend:**
- ✅ `ENVIRONMENT=production`
- ✅ `OPENAI_API_KEY=your_key`
- ✅ `FRONTEND_URL=https://your-netlify-url.netlify.app`

**Netlify Frontend:**
- ✅ `deploy-config.js` has correct `BACKEND_URL`

## File Structure
```
eazewell-agent/
├── static/               # Local development files
│   ├── index.html
│   ├── script.js
│   ├── styles.css
│   └── deploy-config.js
├── deploy-static/        # Production deployment files  
│   ├── index.html
│   ├── script.js
│   ├── styles.css
│   └── deploy-config.js
├── main.py              # FastAPI backend
├── requirements.txt     # Python dependencies
└── DEPLOYMENT.md        # This guide
```