# Radiology VQA Multimodal Agent

A research prototype for **rule-based task evaluation** with a Python CLI, FastAPI service, and offline browser demonstration.

**Important scope limitation:** Despite the historical repository name, this code does **not** load or interpret radiology images, compute vision-language embeddings, or answer image-grounded diagnostic questions. It evaluates supplied numbers and status descriptors against illustrative thresholds. It has not been clinically validated and must not be used for diagnosis, treatment, triage, or patient safety decisions.

## Try the browser demonstration

Open [docs/index.html](docs/index.html) locally in a browser, or view the page through a configured GitHub Pages publication. The interface operates entirely in-browser and does not require Python, Pyodide, a model, or a backend. It supports synthetic task entry, finite-number validation, textual results, and JSON export.

The browser intentionally uses **deterministic JavaScript**, not the Python backend. It mirrors the three generic alert conditions implemented by `agents/workers.py`: primary metric >25, secondary metric >12 or a critical flag, and anomaly keywords in the descriptor. These are **arbitrary demonstration thresholds**, not ACR, Fleischner, ASPECTS, or other validated radiology criteria.

## Python setup

Python 3.10+ is required. From the repository root:

```bash
python -m pip install -e ".[api,test]"
python -m pytest -q
python cli.py audit --task-id TEST-001 --target SYNTHETIC-01 --primary 30 --secondary 5 --status NOMINAL
python cli.py batch -i sample.csv -o results.csv
python cli.py verify-audit
python cli.py chat "What is the system status?"
```

The separately maintained `rad_vqa_agent` package has its own legacy interface:

```bash
python -m rad_vqa_agent.cli audit --task-id TEST-002
```

## Local API

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

The primary FastAPI app (`agents.api:app`) provides `GET /health`, `GET /metrics`, `POST /api/audit`, `POST /api/chat`, and `GET /api/audit/logs`. OpenAPI UI is at `http://127.0.0.1:8000/docs`. The chat endpoint currently uses a **deterministic mock** rather than a medical or general-purpose language model. Non-mock model providers are not implemented and explicitly fail.

An additional `rad_vqa_agent.server` FastAPI implementation exists for the legacy engine; its thresholds differ from the primary `agents` path.

## Container deployment

Generate a strong random key and make it available through the host environment before running:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

The Compose file requires `AUDIT_SECRET_KEY` and binds the API to loopback (`127.0.0.1:8000`) by default. Do not expose the API to untrusted networks: the example service does not implement authentication, access control, rate limits, or persistent storage.

## Data handling and security

- The browser demo makes no network requests, does not store data, and creates JSON downloads locally. Use **synthetic** data.
- The Python application stores dossiers and HMAC-linked audit records **in process memory only**. Audits are not persistent or independently anchored, and the fallback key changes between processes if `AUDIT_SECRET_KEY` is unset.
- The Python identifier filter blocks certain recognizable patterns (e.g., MRNs and email addresses), including text nested in metadata. It is **not** a complete PHI detector, a de-identification method, or evidence of HIPAA compliance.
- The server is a development/research prototype. Do not send real patient information; use synthetic values exclusively.

## Project layout

- `agents/`: primary Pydantic models, rule workers, supervisor, HMAC audit chain, and FastAPI application.
- `rad_vqa_agent/`: separate legacy coordinator and CLI.
- `cli.py`: primary CLI for single-task, batch, chat, audit verification, and API server.
- `enrichment.py`: independent experimental generic-threshold modules; their feature names do not imply implemented image analysis.
- `docs/index.html`: static browser-only demonstration, compatible with GitHub Pages.
- `web/index.html`: equivalent standalone demo for local use.
- `tests/`: unit and regression tests.
- `Dockerfile`, `docker-compose.yml`: local container deployment.

## Development and compatibility

The project uses Python (Pydantic v2, optional FastAPI/Uvicorn), HTML, and vanilla JavaScript. The static demo supports modern browsers with JavaScript enabled and does not require a browser Python runtime. GitHub Actions tests Python 3.10–3.13 and JavaScript syntax. No image inference model, DICOM pipeline, cloud model integration, or clinical validation dataset is included.

Licensed under the [MIT License](LICENSE).
