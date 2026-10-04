<img src="public/banner.svg" style="width: 100%; aspect: square;" />

# PAWM — Personal WorkBook LM

A local-first workspace for thinking with models. PAWM brings profiles, model credentials, reusable tools, and focused workbooks together in one locally run application.

Built with **FastAPI** (backend), **Vue 3 + TypeScript** (frontend), and **JSON-based filesystem storage**. Your data stays on your machine.

---

## Documentation

Full documentation lives in the [`docs/`](docs/) folder:

| Guide | Description |
| --- | --- |
| [Overview](docs/index.html) | What PAWM is and how to find your way around. |
| [Setup](docs/setup.html) | Install Python/Node dependencies and run the app. |
| [User Manual](docs/user-manual.html) | Create profiles and workbooks, add API keys, upload tools. |
| [Project Structure](docs/architecture.html) | How the Vue UI, FastAPI backend, and local data fit together. |

---

## Quick start

### Requirements

- **Python** — required to run the backend.
- **Node.js 22.18+** (or **24.12+**) and **npm** — only needed for frontend development.

### Run the application

From the repository root (PowerShell):

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r Backend/requirements.txt
uvicorn Backend.main:app --port 8080
```

Then open **<http://localhost:8080>**.

- Health check: <http://localhost:8080/health>
- API reference: <http://localhost:8080/docs>

### Frontend development

The backend serves the compiled frontend from `Frontend/`. To develop or rebuild it:

```bash
npm install
npm run dev      # Vite dev server on port 5173
npm run build    # builds into Frontend/ for FastAPI to serve
```

---

## Features

- **Profiles** — top-level workspace boundaries grouping workbooks, API keys, callers, and tools.
- **Workbooks** — a focused place for conversations, sources, and outputs.
- **API keys** — per-profile credentials with base URL, endpoints, and metadata.
- **Tools** — upload trusted ZIP packages (`main.py`, `README.md`, `schema.json`).
- **Callers, sources, and outputs** — model integrations and workbook resources, managed side-by-side.
- **Local-first** — all data is stored on your filesystem. No cloud sync, no accounts.

---

## Repository layout


```.
├── Backend/        FastAPI entry point, routes, services, and models
├── Pawm/           Python filesystem storage API and managers
├── src/            Vue 3 + TypeScript frontend source
├── Frontend/       Built frontend served by FastAPI
├── Storage/        Data directory configured by the web backend
├── public/         Static assets, including LOGO.svg
└── docs/           Static documentation site
```

See the [Project Structure guide](docs/architecture.html) for the full tree and a walkthrough of how a request moves through the system.

---

## Data & privacy

The web backend stores its data in the repository's `Storage/` folder. This includes profile records, API keys, tool packages, and workbook content.

> **Keep `Storage/` private and back it up** if its contents matter to you. It is local filesystem data — not a cloud backup — and may contain credentials or private workbook content.

Do not publish or share your `Storage/` directory. Do not commit it to a public repository.

---

## License

[MIT](LICENSE)
