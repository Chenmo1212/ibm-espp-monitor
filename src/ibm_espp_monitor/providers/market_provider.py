import json
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from ibm_espp_monitor.market_data import (
    MarketDataError,
    MarketDataProvider,
    MarketHistory,
    PricePoint,
)


class YahooMarketProvider(MarketDataProvider):
    """Retrieves standard historical and quote market data from Yahoo Finance API without external SDK."""

    def __init__(self, base_url: str = "https://query1.finance.yahoo.com/v8/finance/chart/"):
        self.base_url = base_url

    def _fetch_chart(self, symbol: str, range_str: str, interval: str = "1d") -> dict:
        url = f"{self.base_url}{symbol}?range={range_str}&interval={interval}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; IBM-ESPP-Monitor/1.0)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise MarketDataError(f"Failed to fetch market data for {symbol}: {e}") from e

        try:
            result = data["chart"]["result"][0]
        except (KeyError, IndexError, TypeError) as e:
            raise MarketDataError(f"Malformed chart response for {symbol}") from e

        return result

    def get_history(self, symbol: str, days: int) -> MarketHistory:
        # Range string can be 1y, 2y, etc. depending on days requested
        range_str = "1y" if days <= 252 else "2y"
        result = self._fetch_chart(symbol, range_str, interval="1d")

        timestamps = result.get("timestamp", [])
        indicators = result.get("indicators", {})
        quote = indicators.get("quote", [{}])[0]
        adjclose_list = indicators.get("adjclose", [{}])[0].get("adjclose", [])
        closes = adjclose_list if adjclose_list else quote.get("close", [])

        prices: list[PricePoint] = []
        for ts, close in zip(timestamps, closes):
            if ts is not None and close is not None:
                try:
                    price_val = Decimal(str(round(close, 4)))
                    if price_val > Decimal("0"):
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        prices.append(PricePoint(timestamp=dt, close_usd=price_val))
                except Exception:
                    continue

        if not prices:
            raise MarketDataError(f"No usable price points for {symbol}")

        return MarketHistory(prices=prices)

    def get_latest(self, symbol: str) -> PricePoint:
        result = self._fetch_chart(symbol, range_str="5d", interval="1d")
        meta = result.get("meta", {})
        regular_price = meta.get("regularMarketPrice")

        if regular_price is not None:
            try:
                price_val = Decimal(str(round(regular_price, 4)))
                if price_val > Decimal("0"):
                    return PricePoint(
                        timestamp=datetime.now(timezone.utc),
                        close_usd=price_val,
                    )
            except Exception:
                pass

        # Fallback to last close in series
        history = self.get_history(symbol, days=5)
        if not history.prices:
            raise MarketDataError(f"No quote data available for {symbol}")
        return history.prices[-1]
