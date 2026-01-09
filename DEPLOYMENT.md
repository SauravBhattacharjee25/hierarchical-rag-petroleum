# 🚀 Hierarchical RAG System - Deployment Guide

## Cloud Deployment Options

### 1. **Render.com** (Recommended - Free Tier)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/SauravBhattacharjee25/hierarchical-rag-petroleum)

**Steps:**
1. Click the button above
2. Connect your GitHub account
3. Set `GEMINI_API_KEY` in environment variables
4. Click Deploy

**Live URL:** `https://your-app-name.onrender.com`

---

### 2. **Railway.app** (Free $5/month credits)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?repo=https://github.com/SauravBhattacharjee25/hierarchical-rag-petroleum)

**Steps:**
1. Click the button above
2. Authorize GitHub
3. Set environment variables
4. Deploy

---

### 3. **Docker** (Local or Any Cloud)
```bash
docker-compose up
```

Access at `http://localhost:8000`

---

### 4. **Heroku** (Legacy)
```bash
heroku login
heroku create your-app-name
git push heroku main
```

---

## Local Deployment Options

### Waitress (Recommended - Pure Python)
```bash
python3 -m waitress --port=8000 --host=0.0.0.0 --threads=4 wsgi:app
```

### Gunicorn (Process Management)
```bash
gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 --worker-class gthread wsgi:app
```

### Uvicorn (Async)
```bash
uvicorn wsgi:app --host 0.0.0.0 --port 8000 --workers 2
```

### Interactive Menu
```bash
python3 deploy.py
```

---

## GitHub Repository
📍 **Your Fork:** https://github.com/SauravBhattacharjee25/hierarchical-rag-petroleum

All code has been pushed. You can now:
- Deploy to cloud platforms
- Clone to other machines
- Contribute back to upstream

---

## Features

✅ **Semantic Search** - BAAI/bge-base-en-v1.5 embeddings  
✅ **Borehole Priority** - S2 > S1 > Main Hole filtering  
✅ **AI Answers** - Gemini integration  
✅ **Well 1 Data** - Pre-configured for petroleum analysis  
✅ **Production Ready** - Gunicorn, Waitress, Docker support  

---

## Environment Variables

```
GEMINI_API_KEY=your_api_key_here
PYTHONUNBUFFERED=1
```

---

## Support

For issues or questions, check:
- `README_.md` - Quick start guide
- `INSTRUCTIONS.md` - Detailed setup
- Backend logs: `docker logs <container>`
