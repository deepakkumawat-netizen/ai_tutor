# 🤖 AI Tutor — Full Stack App

A complete AI-powered CS tutor for K–12 students.  
**Frontend:** React + Vite  
**Backend:** Node.js + Express  
**AI:** Groq API (free) — llama-3.3-70b-versatile

---

## 📁 Project Structure

```
ai-tutor/
├── backend/
│   ├── server.js        ← Express API server
│   ├── .env             ← Your secret API key (never share this!)
│   ├── .env.example     ← Template for .env
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx      ← Main UI component
│   │   ├── api.js       ← Backend API calls
│   │   ├── constants.js ← Curriculum data & helpers
│   │   ├── main.jsx     ← React entry point
│   │   └── index.css    ← Global styles
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md
```

---

## 🚀 Setup & Run

### Step 1 — Get your free Groq API key
1. Go to https://console.groq.com
2. Sign up for free
3. Click **API Keys** → **Create API Key** → copy it

### Step 2 — Configure the backend
```bash
cd backend
```
Open `.env` and replace `your_groq_api_key_here` with your real key:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3 — Install dependencies

**Backend:**
```bash
cd backend
npm install
```

**Frontend:**
```bash
cd frontend
npm install
```

### Step 4 — Run the app

Open **two terminal windows**:

**Terminal 1 — Backend:**
```bash
cd backend
npm run dev
```
You should see: `🚀 AI Tutor backend running at http://localhost:5000`

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
You should see: `➜ Local: http://localhost:5173`

### Step 5 — Open the app
Go to **http://localhost:5173** in your browser ✅

---

## 🔒 Security Features

- ✅ Groq API key stays on the backend — never exposed to the browser
- ✅ Rate limiting (60 requests/minute per IP)
- ✅ Input validation on all endpoints
- ✅ CORS configured to only allow your frontend
- ✅ Content safeguards: off-topic, academic integrity, inappropriate filters

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Server health check |
| GET | `/api/curriculum/:grade` | Get topic for a grade |
| POST | `/api/chat` | Send a message, get AI reply |

---

## 🌐 Deploy to Production

**Backend** → Deploy to [Railway](https://railway.app), [Render](https://render.com), or [Fly.io)  
**Frontend** → Deploy to [Vercel](https://vercel.com) or [Netlify](https://netlify.com)

After deploying the backend, update `frontend/vite.config.js` proxy target to your backend URL.
