# AI CLI Orchestrator - Project Structure

## Overview

This repository has three main areas:

### 1. Main orchestrator app (`backend/` + `frontend/`)

The production multi-agent orchestration platform. Started with `python run.py` from the repo root.

### 2. Downloader page (`downloader_page/`)

Public-facing marketing/download site. Separate FastAPI + React app.

### 3. Installer builder (`release/installer/`)

Scripts that package the orchestrator into Windows/macOS installers.

---

## Workflow

```
┌─────────────────────────────────────────────────────────┐
│ 1. BUILD INSTALLERS (release/installer/)                │
│    python release/installer/build.py                    │
│    ↓                                                     │
│    Creates: orchestrator-setup.exe (Windows)            │
│            orchestrator-setup.dmg (macOS)               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. COPY TO DOWNLOADS (manual or automated)              │
│    cp release/installer/dist/* downloader_page/downloads/ │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. RUN DOWNLOADER PAGE (downloader_page/)               │
│    cd downloader_page && npm run build && npm run backend │
└─────────────────────────────────────────────────────────┘
```

---

## Directory structure

```
IBMbob/
│
├── backend/                      # Main orchestrator API
│   ├── main.py                   # FastAPI entry: backend.main:app
│   ├── config.py
│   ├── api/
│   │   ├── routes/               # REST endpoints under /api/*
│   │   └── websockets/           # /ws/terminals/{id}
│   ├── services/                 # Orchestrator, providers, PTY, agents
│   ├── database/
│   │   ├── init_db.py
│   │   ├── models.py
│   │   └── schema.sql
│   └── requirements.txt
│
├── frontend/                     # React + Vite UI
│   └── src/
│
├── shared/                       # Shared workspace context
│   ├── skill.md
│   ├── plan.md
│   └── sessions/
│
├── docs/                         # Documentation
│   ├── QUICK_START.md            # Main app quick start
│   ├── API.md                    # Main app API
│   ├── ARCHITECTURE.md
│   └── PROJECT_STRUCTURE.md      # This file
│
├── release/
│   └── installer/                # Installer builder
│       ├── backend/              # PyInstaller packaging
│       │   ├── main.py           # Packaged launcher entry
│       │   ├── pyinstaller.spec
│       │   └── build_backend.py
│       ├── launcher/             # Tray launcher (Windows)
│       ├── bootstrapper/         # CLI dependency manager
│       ├── windows/
│       │   ├── setup.iss         # Primary Inno Setup script
│       │   └── installer.iss     # Deprecated legacy script
│       ├── macos/
│       │   └── create_dmg.sh     # macOS DMG builder
│       ├── workspace/            # User workspace templates
│       └── build.py
│
├── downloader_page/              # Download/marketing site (separate app)
│
├── run.py                        # Dev launcher (backend + frontend)
├── README.md
└── LICENSE
```

---

## Key concepts

### Main app

- **Entry:** `python run.py` → uvicorn `backend.main:app`
- **Frontend dev:** Vite on port 5173
- **API docs:** http://localhost:8000/docs

### Installer

- **Primary Windows script:** `release/installer/windows/setup.iss`
- **Backend bundle:** PyInstaller packages repo `backend/` (not legacy `backend/app/`)
- **Build backend:** `cd release/installer/backend && python build_backend.py`

### Downloader page

- Separate codebase under `downloader_page/`
- Serves built installers from `downloader_page/downloads/`
- Not the same API as the main orchestrator

---

## Quick commands

### Main app

```bash
python run.py
python run.py --init-db
python run.py --backend-only
```

### Installer

```bash
cd release/installer
pip install -r backend/requirements.txt

cd backend
python build_backend.py

cd ../windows
python build_windows.py

# macOS
cd ../macos
bash create_dmg.sh
```

### Downloader page

```bash
cd downloader_page
npm install
npm run build
npm run backend
```

---

## Documentation index

| Document | Scope |
|----------|-------|
| [README.md](../README.md) | Project overview |
| [docs/QUICK_START.md](QUICK_START.md) | Main app setup |
| [docs/API.md](API.md) | Main orchestrator API |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [release/installer/README.md](../release/installer/README.md) | Installer builds |
| [downloader_page/README.md](../downloader_page/README.md) | Download site |

---

Last Updated: 2026-05-27
