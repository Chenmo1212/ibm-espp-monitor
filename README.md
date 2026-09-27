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

## How Notifications Work

- 🇬🇧 [Notification Logic (English)](docs/notification-logic.md) — explains the sell signal evaluation and alert rules for readers with no investing background
- 🇨🇳 [通知逻辑说明（中文）](docs/notification-logic-zh.md) — 面向无股票投资背景读者的中文说明

## Running Tests
```bash
source .venv/bin/activate
PYTHONPATH=src pytest -v
```

## Report Format

Each scheduled run sends a Telegram notification in the following format:

```
IBM SELL MONITOR
As of: YYYY-MM-DD HH:MM

Market
Current price: $XXX.XX
180-day percentile: XX.X%
180-day high: $XXX.XX
Distance to 180-day high: -XX.X%
50-day MA: $XXX.XX
200-day MA: $XXX.XX

Portfolio
EUR/USD rate: X.XXXX (live)
Shares: XX.XXXXX
Market value: €XX,XXX.XX ($XX,XXX.XX)
Weighted average cost: $XXX.XX
Unrealised gain: +X.X%
Gain (Pre-tax / Est. Post-tax @33% CGT): €XXX.XX / €XXX.XX
Lots >= 10% gain: X/X

Irish CGT Tax Summary:
- Annual allowance: €1,270.00 (Remaining: €X,XXX.XX, Used: €X.XX)
- Eligible lots gain: Pre-tax €XXX.XX | Est. Post-tax €XXX.XX
  ✅  Eligible gains within annual exemption.
  ℹ️  Verify allowance against other disposals — maintained manually.

Signal: HOLD

Reasons:
- 180-day price percentile: XX.X% (threshold: 85.0%)
- Distance from 180-day high: -XX.X% (threshold: -5.0%)
- Current price >= 50-day MA: no ($XXX.XX vs $XXX.XX)
- 50-day MA >= 200-day MA: no ($XXX.XX vs $XXX.XX)
- Lots with >= 10% gain: X/X

CGT deadline reminder: Disposals in Jan–Nov must be paid by 15 Dec of the same tax year.
Not a price prediction.
```

Signal values: `HOLD` · `SELL_WINDOW`. A `SELL_WINDOW` signal additionally includes an **Execution Guidance** section with tranche-selling advice.
