# AI CLI Orchestrator - Downloader Page & Demo

Complete download page with React frontend for distributing AI CLI Orchestrator installers, and an interactive embedded demo.

---

## 🚀 Quick Start (Local Development)

The backend has been completely removed. This is now a fully standalone, frontend-only project.

### Run Locally:
```bash
python start_frontend.py
```
*This opens the dev server at http://localhost:5173 (React + Vite)*

Alternatively, you can manually run:
```bash
npm install
npm run dev
```

---

## 📦 Installation

### First Time Setup:

```bash
# Install dependencies
npm install
```

---

## 🎯 What's Included

### Frontend (React + TypeScript)
- Modern landing page with dark theme
- Responsive design (mobile, tablet, desktop)
- Smooth animations (Framer Motion)
- **Embedded Interactive Demo** at `/demo`
- Built with Vite for fast development

### Features
- ✅ Beautiful UI and animations
- ✅ Dynamic interactive chat demo (`/demo`)
- ✅ Google Drive direct download links integrated
- ✅ Fully static, frontend-only architecture

---

## 🔧 Development

### Frontend Development:
```bash
python start_frontend.py
# Visit http://localhost:5173
# Changes auto-reload
```

### Production Build:
```bash
# Build frontend
npm run build
```
This generates the static assets inside the `dist` folder which can be easily deployed to Vercel or GitHub Pages.

---

## 🚢 Deployment

### Deploying to Vercel (Recommended)
1. Push this repository to GitHub.
2. Go to your [Vercel Dashboard](https://vercel.com) and import the repository.
3. Vercel will automatically configure the **Framework Preset** to Vite.
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Click **Deploy**.

### Deploying to GitHub Pages
1. Open `vite.config.ts` and add `base: '/your-repo-name/'` inside the `defineConfig` object.
2. Push your code to GitHub.
3. Go to repository Settings > **Pages**.
4. Set the **Source** to **GitHub Actions** and use the Vite deployment workflow.

---

## 📊 Tech Stack

### Frontend
- React 18
- TypeScript
- Vite 6
- Tailwind CSS 4
- React Router
- shadcn/ui components
- Framer Motion
- Lucide icons
- Lenis (Smooth scrolling)

---

## 🤝 Attributions

This project uses the following open-source libraries and resources:

- **shadcn/ui** - [MIT License](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md)
- **React** - [MIT License](https://github.com/facebook/react/blob/main/LICENSE)
- **Tailwind CSS** - [MIT License](https://github.com/tailwindlabs/tailwindcss/blob/master/LICENSE)
- **Framer Motion** - [MIT License](https://github.com/framer/motion/blob/main/LICENSE.md)
- **Lucide React** - [ISC License](https://github.com/lucide-icons/lucide/blob/main/LICENSE)
- **Radix UI** - [MIT License](https://github.com/radix-ui/primitives/blob/main/LICENSE)
- **Lenis** - [MIT License](https://github.com/studio-freight/lenis/blob/main/LICENSE)
- **Vite** - [MIT License](https://github.com/vitejs/vite/blob/main/LICENSE)
- **TypeScript** - [Apache 2.0 License](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt)

---

## 📄 License

MIT License - See LICENSE file for details

---

**Built with ❤️ for the AI CLI Orchestrator project**
