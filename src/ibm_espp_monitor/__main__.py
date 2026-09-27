import argparse
import sys
from ibm_espp_monitor.app import run_once
from ibm_espp_monitor.market_data import MarketDataError


def main() -> None:
    parser = argparse.ArgumentParser(description="IBM ESPP Sell Monitor")
    parser.add_argument(
        "--config",
        default="config/default.toml",
        help="Path to configuration file (default: config/default.toml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate and print report without sending notifications or updating state",
    )
    parser.add_argument(
        "--bot",
        action="store_true",
        help="Start the interactive Telegram bot (long-polling mode)",
    )
    args = parser.parse_args()

    if args.bot:
        try:
            from ibm_espp_monitor.telegram_bot import run_bot
            run_bot()
        except Exception as e:
            print(f"Bot error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        run_once(config_path=args.config, dry_run=args.dry_run)
    except MarketDataError as e:
        print(f"Error fetching market data: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running monitor: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
