# Dota 2 Counter Picker

A tool to help Dota 2 players choose the best heroes to counter their enemies. The project consists of a data pipeline to extract counter data from Dotabuff and a web frontend to visualize and use this data.

## Project Structure

- **`content/`** – All data assets
  - `images/` – hero images (`images/heroes/<slug>.png`)
  - `snapshot/` – raw HTML snapshots (`snapshot/<date>/<slug>.html`)
  - `counter/` – processed JSON (`counter/<date>/<slug>.json` + `metadata.json`)
- **`frontend/`** – Frontend app (serves from `content/` paths)
- **`scripts/`** – Data pipeline scripts
  - `extractor.py` – scrape Dotabuff to `content/snapshot/...`
  - `parser.py` – parse snapshots to `content/counter/...` and write `metadata.json`
  - `icon.py` – download hero images to `content/images/heroes/...`
- **`cli.py`** – Command-line counter picker using `content/counter` data

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
cd frontend && npm install
```

### 2. Extract Data (Optional)
```bash
# Scrape all hero counters from Dotabuff → content/snapshot/<date>/
python scripts/extractor.py

# Parse the scraped data into JSON → content/counter/<date>/
python scripts/parser.py --input-dir content/snapshot/<YYYY-MM-DD> --patch 7.39d

# Download hero images → content/images/heroes/
python scripts/icon.py
```

### 3. Run the Frontend
```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173` and includes:
- Hero counter visualization
- Enemy picker interface
- Interactive hero selection

### 4. Use the CLI (Alternative)
```bash
python cli.py
# Follow prompts to select date and enemy heroes
```

## Data Flow

1. **Extract** → Scrapes Dotabuff counter pages to `./content/snapshot/<date>/`
2. **Parse** → Converts HTML to structured JSON in `./content/counter/<date>/`
3. **Icons** → Downloads hero images to `./content/images/heroes/`
4. **Frontend/CLI** → Uses the processed data to provide counter recommendations

## Requirements

- Python 3.8+
- Node.js 16+
- Google Chrome (for web scraping)
- Selenium WebDriver (auto-installed)