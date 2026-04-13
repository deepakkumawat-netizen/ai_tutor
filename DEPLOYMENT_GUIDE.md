# AI Tutor - Deployment Guide to Render.com

## Prerequisites
- GitHub account (free at github.com)
- Render.com account (free at render.com)
- OpenAI API key (from platform.openai.com/api-keys)
- YouTube API key (optional, from console.cloud.google.com)

---

## Step 1: Create GitHub Repository

### 1a. Initialize Git in the project
```bash
cd C:\AI_tutor\ai-tutor
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 1b. Add all files
```bash
git add .
git commit -m "Initial commit - AI Tutor ready for production"
```

### 1c. Create repository on GitHub
1. Go to github.com/new
2. Repository name: `ai-tutor`
3. Description: "AI-Powered Educational Tutor Platform"
4. Choose "Public" (necessary for free Render deployment)
5. Click "Create repository"

### 1d. Push to GitHub
After creating the repository, GitHub will show you commands. Copy and run:
```bash
git remote add origin https://github.com/YOUR_USERNAME/ai-tutor.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 2: Deploy on Render.com

### 2a. Sign up on Render
1. Go to https://render.com
2. Click "Sign Up"
3. Click "Continue with GitHub"
4. Authorize Render to access your GitHub repositories

### 2b. Create Web Service
1. In Render dashboard, click **"New +"** button
2. Select **"Web Service"**
3. Connect your GitHub account if not already done
4. Find and select **"ai-tutor"** repository
5. Click "Connect"

### 2c. Configure Service
Fill in the deployment form:

| Field | Value |
|-------|-------|
| **Name** | ai-tutor |
| **Environment** | Python 3 |
| **Region** | Oregon (or closest to you) |
| **Branch** | main |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

### 2d. Add Environment Variables
Click on **"Advanced"** → **"Add Environment Variable"**

Add these two variables:

**Variable 1:**
- Key: `OPENAI_API_KEY`
- Value: `sk-proj-YOUR_ACTUAL_API_KEY_HERE` (get from platform.openai.com/api-keys)

**Variable 2:**
- Key: `YOUTUBE_API_KEY`
- Value: `YOUR_YOUTUBE_API_KEY` (optional, leave blank if not needed)

### 2e. Deploy
Click the **"Deploy"** button at the bottom.

Render will start building and deploying your application. This takes 3-5 minutes.

**Status indicators:**
- 🟡 Yellow = Building
- 🔵 Blue = Deploying
- 🟢 Green = Live!

---

## Step 3: Access Your Live Application

Once deployment is complete (green status), you'll see your live URL:

```
https://ai-tutor-xxxxx.onrender.com
```

**Your AI Tutor is now live!** 🎉

---

## Important Notes

### API Key Security
- ✅ Store API keys in Render's environment variables (not in .env file)
- ✅ The .gitignore file prevents .env from being uploaded to GitHub
- ✅ Never commit .env to GitHub!

### Free Tier Limitations
- Free web service goes to sleep after 15 minutes of inactivity
- First request after sleep may take 30 seconds
- Upgrade to paid plan ($7/month) to avoid sleep

### Monitoring Your Deployment
1. In Render dashboard, click on your service
2. View logs in the **"Logs"** tab
3. Check **"Events"** for deployment status

### Updating Your Application
1. Make changes locally
2. Commit and push to GitHub: `git push`
3. Render automatically rebuilds and redeploys!

---

## Troubleshooting

### "Build Failed" Error
- Check the **Logs** tab for specific error
- Ensure requirements.txt has all dependencies
- Verify Python version compatibility

### "Service Crashed" After Deployment
- Check environment variables are set correctly
- Verify OPENAI_API_KEY is valid
- Check logs for specific error messages

### Application Running but Endpoints Return 404
- Ensure startCommand uses: `cd backend && uvicorn server:app ...`
- Verify server.py exports the `app` FastAPI object

### Need to Update Environment Variables
1. In Render dashboard, go to your service
2. Click "Environment"
3. Edit and save variables
4. Service automatically redeploys

---

## What's Next?

### Add Frontend (Optional)
If you want to deploy the frontend too:
1. Create a separate Render "Static Site" service
2. Connect frontend repository
3. Build command: `npm install && npm run build`
4. Publish directory: `dist`

### Custom Domain (Paid Feature)
- Render supports custom domains (requires paid plan)
- Add your domain in "Settings" → "Custom Domains"

### Database (If Needed Later)
- Render offers PostgreSQL, MySQL, Redis
- Add from dashboard when ready

---

## Support

If deployment fails:
1. Check Render logs for error details
2. Verify all environment variables are set
3. Ensure .env is in .gitignore
4. Make sure buildCommand can find requirements.txt
5. Verify startCommand matches your actual entry point

---

## Summary

✅ Code pushed to GitHub  
✅ Render service created  
✅ Environment variables configured  
✅ Application deployed and live!

Your AI Tutor is now accessible to anyone on the internet!

---

**Your Live URL:** `https://ai-tutor-xxxxx.onrender.com`

(Replace xxxxx with your actual service ID shown in Render dashboard)
