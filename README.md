# Forecasting Horserace — Econometric Scaffold

This scaffold is prepared for your five Bloomberg ticker datasets. The game UI is a pixel-art concept; the backend is being organized around genuine out-of-sample forecasting.

## Quick start

### Backend (Python)
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Open `http://localhost:8000/docs`.

### Frontend
```bash
npm install
npm run dev
```

## Data contract for Bloomberg
Use CSV columns like:
- `date`
- `ticker` (optional for multi-ticker files)
- `PX_LAST` or `close`
- `exog_1`, `exog_2`, ... (at least two explanatory series)

For the model inputs, factors must be chronologically aligned and available at the forecast origin. Lag them as needed. The code does not invent factor values. For returns, the loader calculates `100 * log(P_t/P_{t-1})`; this scale convention must be consistent with your model and charts.

## Forecasting methods
- OLS: intercept plus supplied factors, trained with an expanding/rolling estimation window.
- ARIMA: configurable ARIMA order; default `(1,0,1)`.
- ARIMA-GARCH: AR(1) conditional mean plus GARCH(1,1) conditional variance, Student-t errors if `arch` is installed.
- Mean benchmark: zero-return forecast.
- Variance benchmark: historical variance from the current estimation sample.
- Forecast evaluation: RMSE, MAE, directional accuracy, benchmark loss ratios, variance RMSE, QLIKE, and DM tests.

## Reproduce
```bash
python backend/reproduce.py --csv data/ticker.csv --window 500 --evaluation-size 250 --horizon 1 --scheme expanding
```
CSV schema: `returns, exog_1, exog_2, ...`, chronologically sorted.

## Important research notes
- No test/evaluation data may be used for specification selection.
- For a valid OOS test, each forecast is issued using only data available before the target is realized.
- The present `horizon>1` path is a basic fixed-origin evaluation extension. Validate feature/target alignment before relying on multi-step OLS scores.
- A squared daily return is a noisy realized variance proxy; report this limitation.
- Forecast numbers must come from the actual data and code; storyboard/sample screens are illustrative.
- Add data source, Bloomberg field identifiers, extraction date, handling of holidays/missing observations, model diagnostics and limitations to the report.


## Arcade experience update
The start experience is componentized under `src/components/`: landing page, ticker/model setup, Coach Pixel tutorial, Learn More, sound controls, reusable charts/sprites, evaluation report, and winner celebration. `src/utils/audio.js` generates sound effects and looping 8-bit style background music in the browser with Web Audio (no external audio files); browsers require a user gesture before sound can start. Audio can be muted and volume adjusted.

The tutorial uses a scenic pixel-art racetrack background and Coach Pixel's character/dialogue, not embedded/cropped storyboard screenshot panels. Horse running and victory animations are CSS-based.


## Coach Pixel pixel-art refresh
The tutorial now uses `public/pixel/coach-pixel.svg`, a full-body, block-shaded pixel-art Coach Pixel character, and `public/pixel/garden-racetrack.svg`, a garden paddock scene with horses, flower beds, fences, trees and a race track. `CoachTutorial.jsx` uses these assets directly; no storyboard screenshot is displayed in the tutorial. The tutorial background and character animation styles are in `src/style.css`.

## Run locally
```bash
npm install
npm run dev
```
The backend can be started separately using the instructions in the backend README. Until the API is running, the frontend may use its included demo fallback.


## Scene separation
The garden/paddock illustration is used only behind Coach Pixel in the tutorial (`.coach-world`). The actual race remains on the dedicated pixel racetrack (`.race-main` uses `/pixel/race-scene.svg`) with the three model horses animated in their race lanes. The garden horses are standing/grazing background scenery, not competitors.
