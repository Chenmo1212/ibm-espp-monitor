# Notification Logic

This document explains how the IBM ESPP Monitor decides when to send you an alert — written for readers with no background in stocks or investing.

---

## The Big Picture

You own IBM shares through an Employee Stock Purchase Plan (ESPP). The monitor runs on a schedule, checks the current market conditions and your portfolio, and sends you a Telegram message **only when something worth your attention has happened**. It never trades on your behalf.

There are two independent types of alerts:

| Alert | What it means |
|---|---|
| **Sell Window** | Market conditions and your gains look favourable — worth reviewing whether to sell |
| **Concentration Alert** | Your IBM position has grown too large relative to the limit you configured |

---

## Alert 1 — Sell Window

### What is a "sell window"?

Think of it like selling an umbrella. The best time to sell is when it's been raining a lot (demand is high), the price is near its recent peak, and the weather forecast still looks decent. If the price has been falling for months and the trend is downward, it's usually not the right moment.

The monitor checks **four market conditions** and **one portfolio condition**. All five must be true to trigger a Sell Window alert.

---

### The Five Conditions

#### 1. Price percentile ≥ 85% (over 180 days)

The monitor looks at IBM's closing price every day for the past 180 days and ranks today's price within that range. A percentile of 85% means today's price is higher than 85% of all daily prices in the past 6 months — the stock is near the top of its recent range.

> **Analogy:** Imagine the past 6 months of prices laid out from cheapest to most expensive. If today's price falls in the top 15%, this condition is met.

#### 2. Distance from 180-day high ≤ 5%

Even if the price is high by percentile, the monitor also checks that you're not too far below the peak. If the stock hit $300 six months ago but is at $200 today, you're 33% below that high — not a great time to sell. The threshold is 5%: the current price must be within 5% of the 180-day high.

> **Analogy:** If the stock's recent ceiling is $100, the current price must be at least $95.

#### 3. Current price ≥ 50-day moving average

The 50-day moving average (MA) is the average of IBM's closing prices over the past 50 trading days. If today's price is above that average, the short-term trend is upward — the stock has momentum.

> **Analogy:** The 50-day MA is like asking "has this stock been going up more than down lately?" If yes, this condition is met.

#### 4. 50-day MA ≥ 200-day MA (Golden Cross)

The 200-day MA covers roughly a full year of prices. When the shorter 50-day average is above the longer 200-day average, it's a classic sign of a healthy long-term uptrend — sometimes called a "golden cross" in trading.

> **Analogy:** If the short-term mood (50-day) is better than the long-term mood (200-day), the overall trajectory looks positive.

#### 5. At least one lot has ≥ 10% unrealised gain

Your ESPP shares are grouped into "lots" — each purchase event is a separate lot with its own cost basis. This condition checks that at least one lot has grown at least 10% in value since you bought it. There's little point selling if you haven't actually made money.

> **Analogy:** You only want to sell if you can actually lock in a meaningful profit on at least some of what you own.

---

### Signal Levels

The monitor produces one of three signals:

| Signal | Meaning |
|---|---|
| `HOLD` | Neither the market conditions nor the trend look right. Keep holding. |
| `WATCH` | Some conditions are met but not all. Worth monitoring, not acting. |
| `SELL_WINDOW` | All five conditions are met. Worth reviewing your position. |

Only `SELL_WINDOW` triggers a Telegram notification.

---

### Cooldown — No Spam

Once a Sell Window alert is sent, the monitor won't send another one for **30 days** (configurable). This prevents you from receiving repeated alerts during a sustained price run-up.

---

## Alert 2 — Concentration Alert

### What is a concentration risk?

Holding too much of your wealth in a single company's stock is risky — if that company has a bad quarter, your portfolio takes a big hit. This alert fires when the total market value of your IBM shares exceeds a threshold you set (e.g. €12,000).

This check is **independent of the Sell Window**. You can receive a Concentration Alert even during a `HOLD` signal — because the risk of overconcentration exists regardless of whether the price is at a high.

The cooldown for this alert is **90 days** (configurable).

---

## Tax Considerations (Irish CGT)

The monitor also calculates your Irish Capital Gains Tax (CGT) position:

- **Annual exemption:** The first €1,270 of capital gains each tax year is tax-free in Ireland.
- **CGT rate:** Gains above the exemption are taxed at 33%.
- **Deadline reminder:** Gains made between January and November must be paid by **15 December** of the same year.

The report shows both pre-tax and estimated post-tax gains so you can see what you'd actually keep after selling. This is informational only — the monitor never executes trades.

> ⚠️ The monitor only tracks this ESPP. If you've sold other assets during the year, you must manually update `cgt_used_allowance_eur` in the config to avoid over-estimating your remaining exemption.

---

## Summary Flow

```
Every scheduled run
        │
        ▼
Fetch IBM price + 180-day history
        │
        ▼
Calculate metrics (percentile, MAs, lot gains)
        │
        ├─── Concentration check ──► Value > limit? ──► Send Concentration Alert (cooldown: 90d)
        │
        └─── Sell Window check
                │
                All 5 conditions met?
                ├── No  ──► Signal: HOLD or WATCH (no notification)
                └── Yes ──► Signal: SELL_WINDOW ──► Send Sell Window Alert (cooldown: 30d)
```

No trade is ever executed automatically. Every alert is purely informational.
