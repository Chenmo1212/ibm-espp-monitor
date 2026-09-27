# IBM ESPP Portfolio & Sell Monitor

A local, deterministic monitor for IBM Employee Stock Purchase Plan (ESPP) holdings. Evaluates current market positions, 180-day price percentiles, moving averages, and lot-level unrealized gains to generate actionable notifications for sell windows without executing trades.

## Key Features

- **No Automated Trading**: Purely informational alert generator; all sell actions remain manual.
- **Lot-Level Tracking**: Analyzes each purchase lot and dividend reinvestment share independently.
- **Explainable Signals**: Uses deterministic metrics (180-day percentile, distance to 180d high, 50-day & 200-day moving averages, lot unrealized gains) rather than black-box models.
- **Cooldown Support**: Prevents alert fatigue by respecting configured notification cooldown windows.
- **Zero Heavy Dependencies**: Built with Python standard library and `pytest`.

## Installation & Setup

1. **Clone repository and set up virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install pytest
   ```

2. **Configure Settings**:
   Edit [`config/default.toml`](config/default.toml) to adjust thresholds:
   ```toml
   [market]
   lookback_days = 180

   [signal]
   percentile_threshold = 0.85
   high_distance_threshold = 0.05
   min_gain_for_alert = 0.10
   cooldown_days = 30

   [portfolio]
   currency = "EUR"

   [notification]
   enabled = true
   ```

3. **Update Portfolio Records**:
   Keep [`data/espp_lots.csv`](data/espp_lots.csv) updated with your allocation records from Computershare / Fidelity.

## Running the Monitor

### Dry Run / Ad-hoc Check
```bash
./scripts/run_ibm_espp_monitor.sh --dry-run
```

### Scheduled Runs
See [`docs/ibm-espp-monitor.md`](docs/ibm-espp-monitor.md) for launchd (macOS) and cron (Linux) scheduling guides.

## Running Tests
```bash
source .venv/bin/activate
PYTHONPATH=src pytest -v
```
