# Third-party components

Runtime dependencies are declared in `requirements.txt` and resolved in `requirements.lock`: FastAPI, Uvicorn, NumPy, pandas, Numba/llvmlite, DuckDB, Pydantic, HTTPX, python-multipart, pypdf, python-docx, email-validator, python-dotenv and tzdata, plus their transitive dependencies. Their own licenses remain applicable.

The frontend uses native HTML/CSS/JavaScript and project-authored vector icons. jsdom is development-only. Backtesting.py is an AGPL-licensed development-only test oracle and is not imported by the application runtime or installed by its launcher. Model weights, market datasets and proprietary product code are not redistributed. See `docs/RESEARCH.md` for reference products, libraries and licensing choices.
