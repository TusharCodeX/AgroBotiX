# Deploying AgriPath to Vercel

This repository is fully configured for **1-click deployment on [Vercel](https://vercel.com)**.

---

## Architecture Overview

1. **Frontend on Vercel**: High-performance React + Vite + Tailwind CSS interface served via Vercel's global edge network.
2. **Interactive Standalone Fallback**: When viewed on Vercel without a backend attached, AgriPath automatically enters **Vercel Cloud Demo Mode**, enabling field presets, perception simulation, skid-steer path planning, and rover animations with zero configuration.
3. **Live AI Backend**: To connect real-time YOLOv8 ONNX inference and physical rover serial communication, you can connect any deployed FastAPI instance (Render, Railway, Fly.io, or ngrok).

---

## Method 1: Deploy via GitHub (Recommended)

1. **Push your repository to GitHub**:
   ```bash
   git add .
   git commit -m "Configure AgriPath for Vercel deployment"
   git push origin main
   ```

2. **Import to Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new) and log in.
   - Click **Import** next to your GitHub repository.
   - **Vercel Settings**:
     - The root [`vercel.json`](./vercel.json) automatically sets:
       - **Framework Preset**: Vite
       - **Build Command**: `cd frontend && npm install && npm run build`
       - **Output Directory**: `frontend/dist`
   - *(Optional)* If you have a deployed backend URL, add an Environment Variable:
     - Key: `VITE_API_BASE_URL`
     - Value: `https://your-backend-service.onrender.com`
   - Click **Deploy**!

---

## Method 2: Deploy via Vercel CLI

1. **Install Vercel CLI**:
   ```powershell
   npm install -g vercel
   ```

2. **Deploy directly from the project directory**:
   ```powershell
   vercel
   ```
   Follow the CLI prompts:
   - Set up and deploy? `y`
   - Which scope? Select your account
   - Link to existing project? `n`
   - Project name? `agripath`
   - In which directory is your code located? `./`
   - Want to modify settings? `n` (all settings are handled by `vercel.json`)

3. **Deploy to Production**:
   ```powershell
   vercel --prod
   ```

---

## Connecting the Real YOLOv8 ONNX Backend

Because Computer Vision and PyTorch/ONNX Runtime require native C++ runtime libraries and larger bundle sizes than Vercel Serverless limits, the Python backend can be hosted on a container host:

### Option A: Free Docker Hosting on Render or Railway
1. Push this repo to GitHub.
2. In [Render](https://render.com) or [Railway](https://railway.app):
   - Choose **New Web Service** -> Select your repo.
   - Environment: **Docker** (uses our provided [`Dockerfile`](./Dockerfile)).
   - Port: `8000`
3. Copy your service URL (e.g., `https://agripath-backend.onrender.com`).
4. In your Vercel Dashboard, go to **Settings > Environment Variables**:
   - Add `VITE_API_BASE_URL = https://agripath-backend.onrender.com`
   - Redeploy the frontend.

### Option B: Direct Tunnel from Local Machine / Rover (Quick Demo)
If running AgriPath locally or on a Raspberry Pi:
```powershell
# In another terminal:
npx ngrok http 8000
```
Copy the generated `https://xxxx.ngrok-free.app` URL and paste it into:
- **AgriPath Settings Modal > FastAPI Backend URL** (inside the web app).
- Changes take effect immediately without redeploying!
