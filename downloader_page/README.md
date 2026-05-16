# AI CLI Orchestrator - Downloader Page

Complete download page with React frontend and FastAPI backend for distributing AI CLI Orchestrator installers.

---

## 🚀 Quick Start (Run Everything)

### Windows - One Command:
```bash
cd downloader_page
start.bat
```

This opens 2 terminals:
- **Frontend**: http://localhost:5173 (React + Vite)
- **Backend**: http://localhost:8000 (FastAPI)

### Manual Start (Any OS):

**Terminal 1 - Frontend:**
```bash
cd downloader_page
npm run dev
```

**Terminal 2 - Backend:**
```bash
cd downloader_page/backend
python run.py
```

---

## 📦 Installation

### First Time Setup:

```bash
# Install frontend dependencies
npm install

# Install backend dependencies
pip install -r backend/requirements.txt
```

---

## 🎯 What's Included

### Frontend (React + TypeScript)
- Modern landing page with dark theme
- Responsive design (mobile, tablet, desktop)
- Smooth animations (Framer Motion)
- Download buttons with API integration
- Built with Vite for fast development

### Backend (FastAPI + Python)
- Serves React frontend
- REST API for version info
- Automatic installer detection
- File serving for downloads
- Health check endpoints

### Features
- ✅ Automatic installer detection
- ✅ Dynamic download availability
- ✅ File size display
- ✅ Platform-specific downloads
- ✅ API documentation (Swagger UI)
- ✅ Hot reload in development

---

## 📥 Download Functionality

### Current Status:
- ✅ Windows: Available (dummy file for testing)
- ✅ macOS: Available (dummy file for testing)
- ❌ Linux: Not available

### How It Works:
1. Backend scans `downloads/` folder
2. Detects installer files by name
3. API returns availability status
4. Frontend shows/hides download buttons
5. Users click to download

### File Names (Must Match Exactly):
- `AI-CLI-Orchestrator-Setup.exe` (Windows)
- `AI-CLI-Orchestrator-Setup.dmg` (macOS)
- `AI-CLI-Orchestrator-Setup.AppImage` (Linux)

---

## 🔧 Development

### Frontend Development:
```bash
npm run dev
# Visit http://localhost:5173
# Changes auto-reload
```

### Backend Development:
```bash
cd backend
python run.py
# Visit http://localhost:8000
# Changes auto-reload
```

### Production Build:
```bash
# Build frontend
npm run build

# Start backend (serves built frontend)
npm run backend

# Access at http://localhost:8000
```

---

## 🌐 API Endpoints

### GET /
Serves the React frontend

### GET /api/version
Returns version info and download links

**Response:**
```json
{
  "version": "1.0.0",
  "release_date": "2026-05-16",
  "downloads": {
    "windows": {
      "url": "/downloads/AI-CLI-Orchestrator-Setup.exe",
      "size": 12345678,
      "available": true
    },
    "macos": {
      "url": "/downloads/AI-CLI-Orchestrator-Setup.dmg",
      "size": 12345678,
      "available": true
    },
    "linux": {
      "available": false
    }
  },
  "checksums": {
    "windows": "sha256:...",
    "macos": "sha256:..."
  }
}
```

### GET /api/health
Health check endpoint

### GET /api/docs
Interactive API documentation (Swagger UI)

### GET /downloads/{filename}
Download installer files

---

## 📦 Adding Real Installers

### Step 1: Build Installers
```bash
cd ../installer

# Build Windows installer
python build.py --windows

# Build macOS installer
python build.py --macos

# Build all platforms
python build.py --all
```

### Step 2: Copy to Downloads Folder
```bash
# From installer directory
cp dist/AI-CLI-Orchestrator-Setup.exe ../downloader_page/downloads/
cp dist/AI-CLI-Orchestrator-Setup.dmg ../downloader_page/downloads/
```

### Step 3: Restart Backend
The backend will automatically detect the new files!

---

## 📁 Project Structure

```
downloader_page/
├── src/                          # React frontend source
│   ├── app/
│   │   ├── App.tsx              # Main component
│   │   └── components/
│   │       ├── Navbar.tsx       # Navigation
│   │       ├── Hero.tsx         # Hero section
│   │       ├── PainPoints.tsx   # Problem statement
│   │       ├── Features.tsx     # Features grid
│   │       ├── DownloadCTA.tsx  # Download section
│   │       └── ui/              # UI components
│   └── styles/                  # CSS files
│
├── backend/                      # FastAPI backend
│   ├── __init__.py
│   ├── main.py                  # FastAPI app
│   ├── run.py                   # Dev server
│   └── requirements.txt         # Python deps
│
├── downloads/                    # Installer files
│   ├── AI-CLI-Orchestrator-Setup.exe
│   ├── AI-CLI-Orchestrator-Setup.dmg
│   └── README.md
│
├── dist/                         # Built frontend
├── node_modules/                 # Node dependencies
├── package.json                  # Frontend deps
├── vite.config.ts               # Vite config
├── start.bat                    # Windows startup script
└── README.md                    # This file
```

---

## 🛠️ Troubleshooting

### Frontend Won't Start
```bash
# Reinstall dependencies
rm -rf node_modules
npm install
npm run dev
```

### Backend Won't Start
```bash
# Reinstall dependencies
cd backend
pip install -r requirements.txt
python run.py
```

### Downloads Not Working
1. Check backend is running: http://localhost:8000/api/health
2. Check files exist in `downloads/` folder
3. Check file names match exactly
4. Check browser console for errors
5. Try API directly: http://localhost:8000/api/version

### Port Already in Use

**Frontend (5173):**
```bash
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5173 | xargs kill -9
```

**Backend (8000):**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### CORS Errors
Update `allow_origins` in `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Specific origin
    # or
    allow_origins=["*"],  # All origins (dev only)
)
```

---

## 🚢 Deployment

### Option 1: Single Server (Recommended)

1. **Build frontend:**
```bash
npm run build
```

2. **Upload to server:**
- Upload entire `downloader_page/` directory
- Include `dist/`, `backend/`, `downloads/`

3. **Install backend dependencies:**
```bash
pip install -r backend/requirements.txt
```

4. **Run backend:**
```bash
python backend/run.py
```

5. **Configure reverse proxy (nginx):**
```nginx
server {
    listen 80;
    server_name download.yoursite.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 2: Separate Hosting

**Frontend → Static Hosting (Vercel/Netlify):**
1. Build: `npm run build`
2. Deploy `dist/` folder
3. Update API URLs in code

**Backend → Server/Cloud:**
1. Deploy `backend/` directory
2. Install dependencies
3. Run with production WSGI server
4. Update CORS settings

---

## 🔒 Security Notes

### Windows SmartScreen Warning
Downloaded `.exe` files will show a security warning because:
- File is not digitally signed
- No established reputation with Microsoft

**To fix:**
1. Get a code signing certificate
2. Sign the installer with `signtool.exe`
3. Build reputation over time

### Production Checklist
- [ ] Restrict CORS origins
- [ ] Add rate limiting
- [ ] Enable HTTPS
- [ ] Generate file checksums
- [ ] Sign installers
- [ ] Add download analytics
- [ ] Monitor server logs

---

## 📊 Tech Stack

### Frontend
- React 18
- TypeScript
- Vite 6
- Tailwind CSS 4
- shadcn/ui components
- Framer Motion
- Lucide icons

### Backend
- FastAPI
- Uvicorn
- Python 3.8+
- Pydantic
- CORS middleware

---

## 📝 Available Scripts

```bash
# Development
npm run dev              # Start frontend dev server
npm run backend          # Start backend server
start.bat               # Start both (Windows)

# Production
npm run build           # Build frontend
npm run preview         # Preview production build

# Backend
npm run backend:install # Install backend dependencies
```

---

## 🔗 URLs

- **Frontend Dev**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Version Info**: http://localhost:8000/api/version
- **Health Check**: http://localhost:8000/api/health

---

## 📚 Additional Documentation

- [`downloads/README.md`](downloads/README.md) - Installer files info
- [`../installer/README.md`](../installer/README.md) - Installer build docs
- [`../PROJECT_STRUCTURE.md`](../PROJECT_STRUCTURE.md) - Project overview

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🆘 Support

- **Issues**: Create a GitHub issue
- **Documentation**: Check this README
- **API Docs**: Visit /api/docs when backend is running

---

**Built with ❤️ for the AI CLI Orchestrator project**

Last Updated: 2026-05-16