# Python Backend Setup (FastAPI)

## Quick Start

### 1. Install Python 3.12+
```bash
python --version  # Should show 3.12+
```

### 2. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Build Frontend (One time)
```bash
cd frontend
npm install
npm run build
```

### 4. Run Python Backend
```bash
cd backend
python server.py
```

Server will start on **http://localhost:5000**

## What Changed

✅ **Single Python server** serves frontend + API
✅ **No CORS issues** - same origin
✅ **Fast deployment** - one command to run
✅ **Port 5000** - both frontend and API on same port
✅ **All endpoints working** - YouTube, Topics, Explain, Questions

## API Endpoints

- `POST /api/mcp/get-topics` - Get topics for subject
- `POST /api/mcp/explain-topic` - Explain a topic
- `POST /api/mcp/practice-question` - Generate practice question
- `POST /api/youtube` - Search YouTube videos

## File Structure

```
backend/
  ├── server.py           (← FastAPI server - serves frontend + API)
  ├── requirements.txt    (← Python dependencies)
  └── .env               (← Your API keys)

frontend/
  └── dist/              (← Built React app)
```

## Environment Variables

Same `.env` file as before:
```
OPENAI_API_KEY=sk-proj-...
YOUTUBE_API_KEY=AIza...
PORT=5000
```

## Troubleshooting

**Port 5000 in use?**
```bash
# Change port in .env
PORT=5001
python server.py
```

**Module not found?**
```bash
pip install -r requirements.txt --upgrade
```

**Frontend not showing?**
```bash
cd frontend
npm run build  # Build frontend first
cd ../backend
python server.py
```

## Performance

- ✅ Single process (no separate frontend server)
- ✅ Static files served directly
- ✅ No CORS overhead
- ✅ Faster startup
- ✅ Easier deployment to production

## Stopping Server

Press `Ctrl+C` in the terminal
