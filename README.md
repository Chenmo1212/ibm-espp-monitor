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

## Report Format

Each scheduled run sends a Telegram notification in the following format:

```
IBM SELL MONITOR
As of: 2026-09-27 18:18

Market
Current price: $225.51
180-day percentile: 15.0%
180-day high: $326.89
Distance to 180-day high: -31.0%
50-day MA: $230.16
200-day MA: $254.81

Portfolio
EUR/USD rate: 1.1401 (live)
Shares: 52.52768
Market value: €10,389.89 ($11,845.52)
Weighted average cost: $216.14
Unrealised gain: +4.3%
Gain (Pre-tax / Est. Post-tax @33% CGT): €431.55 / €431.55
Lots >= 10% gain: 5/9

Irish CGT Tax Summary:
- Annual allowance: €1,270.00 (Remaining: €1,270.00, Used: €0.00)
- Eligible lots gain: Pre-tax €598.19 | Est. Post-tax €598.19
  ✅  Eligible gains within annual exemption.
  ℹ️  Verify allowance against other disposals — maintained manually.

Signal: HOLD

Reasons:
- 180-day price percentile: 15.0% (threshold: 85.0%)
- Distance from 180-day high: -31.0% (threshold: -5.0%)
- Current price >= 50-day MA: no ($225.51 vs $230.16)
- 50-day MA >= 200-day MA: no ($230.16 vs $254.81)
- Lots with >= 10% gain: 5/20

CGT deadline reminder: Disposals in Jan–Nov must be paid by 15 Dec of the same tax year.
Not a price prediction.
```

Signal values: `HOLD` · `SELL_WINDOW`. A `SELL_WINDOW` signal additionally includes an **Execution Guidance** section with tranche-selling advice.
