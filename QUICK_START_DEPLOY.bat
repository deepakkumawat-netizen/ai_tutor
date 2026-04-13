@echo off
REM AI Tutor - Quick Deployment Script
REM This script pushes your code to GitHub and deploys to Render.com

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI TUTOR - QUICK START DEPLOYMENT
echo ============================================================
echo.

REM Check if Git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed!
    echo Please install Git from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo [Step 1] Checking Git repository...
if not exist .git (
    echo [INFO] Initializing Git repository...
    git init
    git config user.name "AI Tutor Developer"
    git config user.email "ai-tutor@example.com"
) else (
    echo [OK] Git repository already initialized
)

echo.
echo [Step 2] Adding files...
git add .
echo [OK] Files staged

echo.
echo [Step 3] Creating commit...
git commit -m "Deploy AI Tutor to Render.com" 2>nul
if errorlevel 1 (
    echo [INFO] No new changes to commit
) else (
    echo [OK] Commit created
)

echo.
echo ============================================================
echo   NEXT STEPS
echo ============================================================
echo.
echo 1. Go to: https://github.com/new
echo    - Name: ai-tutor
echo    - Make it PUBLIC (important!)
echo    - Click "Create repository"
echo.
echo 2. Copy the commands shown on GitHub and run them:
echo    git remote add origin https://github.com/YOUR_USERNAME/ai-tutor.git
echo    git branch -M main
echo    git push -u origin main
echo.
echo 3. Go to: https://render.com
echo    - Sign up with GitHub
echo    - Click "New Web Service"
echo    - Select your ai-tutor repository
echo    - Fill in the configuration as shown in DEPLOYMENT_GUIDE.md
echo    - Add OPENAI_API_KEY environment variable
echo    - Click Deploy!
echo.
echo 4. Wait 3-5 minutes for deployment to complete
echo.
echo For detailed instructions, see: DEPLOYMENT_GUIDE.md
echo.
echo ============================================================
echo.
pause
