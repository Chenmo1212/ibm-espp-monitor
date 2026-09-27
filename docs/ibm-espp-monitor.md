# IBM ESPP Monitor Operational Documentation

## Overview

The IBM ESPP Monitor evaluates historical ESPP purchases against IBM market dynamics to flag favorable rebalancing or profit-taking windows.

## Signal Semantics

The monitor emits one of three deterministic statuses based on market conditions and lot profitability:

- **`SELL_WINDOW`**:
  - 180-day price percentile $\ge$ `percentile_threshold` (default 85%).
  - Current price is within `high_distance_threshold` of 180-day high (default within 5%).
  - Positive trend: Current price $\ge$ 50-day MA $\ge$ 200-day MA.
  - Portfolio condition: At least one lot has $\ge$ `min_gain_for_alert` unrealized gain (default 10%).
- **`WATCH`**:
  - Market conditions are elevated or trending positively, but either not all market criteria or no lot-level profit thresholds are met.
- **`HOLD`**:
  - The configured sell-window conditions are not present.

*Note: None of these statuses constitutes financial advice or a prediction of future stock price movements.*

## Notification Setup

To enable Telegram notifications:
Set the environment variables prior to running:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## Scheduling

The monitor is intended to run once daily after US market close (4:00 PM EST / 9:00 PM UTC).

### Linux (cron)

Open crontab (`crontab -e`) and add:
```cron
30 22 * * 1-5 /path/to/ibm-espp-monitor/scripts/run_ibm_espp_monitor.sh >> /path/to/ibm-espp-monitor/logs/monitor.log 2>&1
```

*Note: Ensure you account for local timezone differences and Daylight Saving Time shifts relative to US market hours.*

### macOS (launchd)

Create a LaunchAgent plist at `~/Library/LaunchAgents/com.ibm.espp.monitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ibm.espp.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/path/to/ibm-espp-monitor/scripts/run_ibm_espp_monitor.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>22</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/ibm_espp_monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ibm_espp_monitor_err.log</string>
</dict>
</plist>
```

Load the job:
```bash
launchctl load ~/Library/LaunchAgents/com.ibm.espp.monitor.plist
```
