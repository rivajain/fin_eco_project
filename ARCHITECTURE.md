# Architecture

- `src/`: React/Vite presentation layer.
- `backend/main.py`: FastAPI endpoint layer.
- `backend/evaluation.py`: independent modeling and evaluation routines.
- `backend/data/load_bloomberg.py`: ingestion and validation of Bloomberg CSV files.
- `backend/reproduce.py`: standalone reproducibility entry point.
- `design/`: reference storyboard.

The frontend should call the API and render returned metrics/forecasts. Do not calculate separate client-side metrics that can disagree with the backend. The final submission should include one source of truth for model fitting and evaluation.
