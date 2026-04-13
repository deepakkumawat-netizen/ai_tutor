# 🔒 Security Guide - AI Tutor

## Critical: API Keys Management

### ⚠️ If Keys Are Compromised
If your `.env` file with API keys has been exposed:

1. **Immediately regenerate all API keys:**
   - OpenAI: https://platform.openai.com/api-keys
   - YouTube: https://console.cloud.google.com/
   - LangChain: https://smith.langchain.com

2. **Update your `.env` file** with new keys

3. **Never commit `.env` to git** (it's in `.gitignore`)

---

## Setup Instructions

### 1. Create Your `.env` File

Copy the template to create your actual environment file:

```bash
# In /backend directory
cp .env.example .env
```

Then edit `.env` and add your real API keys:

```
OPENAI_API_KEY=sk-proj-your-real-key
YOUTUBE_API_KEY=your-real-youtube-key
LANGCHAIN_API_KEY=your-real-langchain-key
```

### 2. Verify `.gitignore` Is Set Up

Make sure `.gitignore` contains:
```
.env
.env.local
.env.*.local
```

This prevents accidentally committing secrets to git.

### 3. Check What's in Git

```bash
git status
```

You should NOT see `.env` listed. If you do, run:

```bash
git rm --cached .env
git commit -m "Remove .env from git tracking"
```

---

## Best Practices

✅ **DO:**
- Keep `.env` files locally only
- Use different keys for dev, staging, and production
- Rotate keys regularly
- Use `.env.example` as a template
- Document required environment variables

❌ **DON'T:**
- Commit `.env` to git
- Share API keys in messages or emails
- Use the same key for multiple projects
- Log or print API keys
- Include keys in error messages

---

## Environment Variables Reference

### Backend (`/backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI GPT-4o-mini API key |
| `YOUTUBE_API_KEY` | ✅ Yes | YouTube Data API v3 key |
| `LANGCHAIN_API_KEY` | ❌ No | Optional - for tracing/debugging |
| `PORT` | ❌ No | Server port (default: 5000) |
| `FRONTEND_URL` | ❌ No | CORS allowed origins |

### Frontend (`/frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | ❌ No | Backend API URL (default: http://localhost:5000) |

---

## Getting API Keys

### OpenAI API
1. Go to: https://platform.openai.com/api-keys
2. Sign in with your OpenAI account
3. Click "Create new secret key"
4. Copy and paste into `.env`

### YouTube API
1. Go to: https://console.cloud.google.com/
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create credentials (API key)
5. Copy and paste into `.env`

### LangChain (Optional)
1. Go to: https://smith.langchain.com
2. Sign in
3. Create API key in settings
4. Copy and paste into `.env`

---

## Production Deployment

For production, use your hosting provider's secret management:

- **Vercel**: Use Environment Variables in project settings
- **Railway**: Use Variables section
- **AWS**: Use AWS Secrets Manager
- **Google Cloud**: Use Secret Manager

Never hardcode keys in the codebase!

---

## Monitoring

Watch for unauthorized API usage:

- **OpenAI**: Check https://platform.openai.com/usage/overview
- **YouTube**: Check https://console.cloud.google.com/apis/dashboard

If you see unusual activity, regenerate keys immediately.

---

## Questions?

If you suspect a security issue:
1. Regenerate all API keys
2. Check git history with: `git log --all -- '*.env'`
3. Rotate keys immediately
4. Update `.env` locally

Stay safe! 🔐
