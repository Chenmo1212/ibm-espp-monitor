# IBM ESPP 投资组合监控与再平衡/卖出评估系统 — 技术与业务逻辑评估报告

---

## 1. Executive Summary（系统定位与概述）

- **项目名称**：IBM ESPP Portfolio & Sell Monitor
- **定位**：面向爱尔兰地区 IBM 员工的 ESPP（员工股票购买计划）与 DRIP（股息再投资）持股的**确定性（Deterministic）、轻量化辅助监控与再平衡提醒工具**。
- **设计哲学**：
  - **辅助决策，绝不自动下单（No Automated Trading）**：所有买卖均由投资者在券商（Computershare / Fidelity）端手动执行。
  - **可维护性与高信噪比优先于复杂模型**：不使用黑盒机器学习，不引入高频震荡指标（如 RSI、ATR、自适应阈值等），依托日频收盘价、均线与持仓批次收益做中低频监控。
  - **爱尔兰本土化税务与风险双轨驱动**：集成爱尔兰 CGT（33% 资本利得税）、年度免税额度（€1,270）追踪、CGT 缴税申报期限提醒，以及**独立于择时信号的持仓集中度风控引擎**。

---

## 2. 核心架构与数据流图

```mermaid
flowchart TD
    subgraph Data_Inputs [数据输入层]
        A["ESPP 持仓批次 (data/espp_lots.csv)\n- 日期 / 股数 / 成本价 / 类别"]
        B["市场行情 (Yahoo / Market Provider)\n- IBM 日频历史收盘价 (>=180d)"]
        C["系统配置 (config/default.toml)\n- 阈值 / 汇率 / 爱尔兰 CGT 参数 / 集中度上限"]
    end

    subgraph Dual_Engine [双轨计算与决策层]
        direction TB
        
        subgraph Engine_1 [轨1: 市场与收益择时引擎 (30天冷却)]
            B --> D["计算市场指标\n- 180天分位数 (>=85%)\n- 距180天高点差距 (<=5%)\n- 多头均线 (Price >= MA50 >= MA200)"]
            A & B --> E["批次收益分析\n- 每批次浮盈率 (gain_percent)\n- 收益达标批次筛选 (>=10%)"]
            D & E --> F{"综合状态评估"}
            F -->|三项共振| G["SELL_WINDOW (卖出窗口)"]
            F -->|部分满足| H["WATCH (观察)"]
            F -->|未满足| I["HOLD (持有)"]
        end

        subgraph Engine_2 [轨2: 组合集中度风控引擎 (90天独立冷却)]
            A & B & C --> J["持仓总市值折算 (EUR)\nTotal Shares * Price / FX"]
            J --> K{"是否超过上限?\nTotal Value > max_position_value_eur"}
            K -->|是| L["CONCENTRATION_ALERT (超标减仓告警)"]
            K -->|否| M["集中度正常"]
        end
    end

    subgraph Tax_Layer [爱尔兰 CGT 税务计算层]
        E --> N["税前收益 (Pre-tax Gain EUR)"]
        N --> O["预估税后收益 (Post-tax EUR = Gain * 0.67)"]
        N & C --> P["年度免税额 (€1,270) 校验与超额预警"]
        Q["系统日期 (as_of)"] --> R["CGT 缴税截止日提醒\n- 1~11月卖出: 当年12月15日前\n- 12月卖出: 次年1月31日前"]
    end

    subgraph Output_Layer [报告与通知层]
        G & H & I & O & P & R --> S["标准监控报告 (渲染终端 / Telegram)"]
        L & R --> T["集中度超标告警 (独立推送)"]
    end
```

---

## 3. 核心业务与算法逻辑详析

### 3.1 择时信号引擎（Market & Lot Timing Engine）
系统将市场状态与持仓批次表现结合，输出三态决策（`SELL_WINDOW` / `WATCH` / `HOLD`）：

1. **市场高位判定（Market High）**：
   - 过去 180 观察日价格百分位数 $\ge 85\%$：
     $$\text{Percentile}_{180d} = \frac{\sum_{i=1}^{N} \mathbb{I}(P_i \le P_{current})}{N} \ge 0.85$$
   - 距过去 180 观察日最高价差距在 $5\%$ 容差内：
     $$\text{Distance to High} = \frac{P_{current} - \max(P_{180d})}{ \max(P_{180d})} \ge -0.05$$
2. **多头趋势保护（Positive Trend Alignment）**：
   - 价格位于 50 日均线之上，且 50 日均线高于 200 日均线：
     $$P_{current} \ge MA_{50} \ge MA_{200}$$
   - *设计目的*：防止在下行破位或超跌反弹中盲目发出卖出信号，确保只在上涨趋势的高位提示。
3. **持仓盈利达标（Lot Profitability）**：
   - 独立计算每个 Lot 的未实现收益率：
     $$\text{Gain}_k = \frac{P_{current} - \text{Cost}_k}{\text{Cost}_k} \ge 10\%$$
   - 只有至少存在 1 个批次收益 $\ge 10\%$ 时，才具备卖出前置条件。
4. **分批卖出操作指引（Tranche Execution）**：
   - 触发 `SELL_WINDOW` 时，系统在报告中输出：
     > `💡 建议分批卖出 (例如先卖出 1/3)，若价格继续创出新高可保留剩余批次继续观察。`
   - *设计目的*：以极简的人工规则应对主升浪突破时的“过早卖飞”问题，避免增加复杂的动量追踪算法。

---

### 3.2 独立集中度风控引擎（Concentration Risk Engine）
- **触发逻辑**：
  $$\text{Total Market Value (EUR)} = \frac{\sum (\text{Quantity}_k \times P_{current})}{\text{FX}_{\text{EUR/USD}}}$$
  $$\text{Condition: } \text{Total Market Value (EUR)} > \text{max\_position\_value\_eur} \quad (\text{如 } \text{€}10,000)$$
- **业务机制**：
  - **无视择时**：无论市场处于 `HOLD`、`WATCH` 还是 `SELL_WINDOW`，只要单一标的持仓金额超过用户设定的硬性上限，均触发独立的集中度告警。
  - **建议优先级**：优先提示减仓至安全限额以下，防范单一雇主股票过度集中的风险（劳动力收入 + 资产净值双重暴露）。

---

### 3.3 爱尔兰本土化 CGT 税务模型（Irish CGT Tax Rules）

针对爱尔兰税务居民，移除了美国 Sec. 423(b) 的持股期限区分，实行以下爱尔兰税务规则：

1. **统一 33% 资本利得税率与年度免税额度扣减**：
   - 税前收益：$\text{Gain}_{\text{EUR}} = \frac{\text{Market Value}_{\text{USD}} - \text{Cost Value}_{\text{USD}}}{\text{FX}}$
   - 爱尔兰个人每年享有 **€1,270** 的 CGT 免税额度。
   - 剩余可用免税额度：$\text{Remaining Allowance} = \max(0, \text{cgt\_annual\_allowance\_eur} - \text{cgt\_used\_allowance\_eur})$
   - **预估税后净收益精确算法**：
     $$\text{Tax Free Portion} = \min(\text{Gain}_{\text{EUR}}, \text{Remaining Allowance})$$
     $$\text{Taxable Gain} = \max(0, \text{Gain}_{\text{EUR}} - \text{Remaining Allowance})$$
     $$\text{Post-tax Gain}_{\text{EUR}} = \text{Tax Free Portion} + \text{Taxable Gain} \times (1 - 0.33)$$
   - *说明*：若收益未超过剩余免税额度，全部免税；超出部分按 33% 计税。
2. **年度免税额追踪与多资产占用提示**：
   - `cgt_used_allowance_eur` 需用户在当年完成任意资产出售后手动维护。
   - 脚本在报告中明确提示：*系统无法感知本 ESPP 之外的其他资产交易（如其他股票、基金、加密货币等），需自行核实该免税额是否已被占用*。
3. **爱尔兰税务申报与缴税期限智能提醒（Tax Deadlines）**：
   - **当年 1 月 1 日 ~ 11 月 30 日** 卖出：
     > `ℹ️ 税务申报期限提醒: 1月-11月发生的卖出，须于当年 12 月 15 日前完成 CGT 缴税。`
   - **当年 12 月 1 日 ~ 12 月 31 日** 卖出：
     > `ℹ️ 税务申报期限提醒: 12月发生的卖出，须于次年 1 月 31 日前完成 CGT 缴税。`

---

### 3.4 状态持久化与双轨独立冷却机制（Dual Cooldown State）

在 `data/notification_state.json` 中独立记录两类通知时间戳，避免告警疲劳且互不干扰：

| 告警类别 | 默认冷却周期 | 触发条件 | 核心诉求 |
| :--- | :---: | :--- | :--- |
| **`SELL_WINDOW` 择时告警** | **30 天** | 市场高位 + 顺势 + 批次盈利 | 周期性获利了结，防止高频交易与告警疲劳 |
| **`CONCENTRATION_ALERT` 集中度告警** | **90 天** | 持仓总市值超过上限 | 资产配置风控，低频强提醒 |

---

## 4. 示例报告输出

### 4.1 标准每日监控报告（触发 `SELL_WINDOW` 时）
```text
IBM SELL MONITOR
As of: 2026-09-27 18:00

Market
Current price: $275.00
180-day percentile: 100.0%
180-day high: $275.00
Distance to 180-day high: 0.0%
50-day MA: $255.35
200-day MA: $232.85

Portfolio
Shares: 52.52768
Market value: €13,375.10 ($14,445.11)
Weighted average cost: $216.14
Unrealised gain: +27.2%
Gain (Pre-tax / Est. Post-tax @33% CGT): €2,862.60 / €2,337.04
Lots >= 10% gain: 14/19

Irish CGT Tax Summary:
- Annual allowance: €1,270.00 (Remaining: €1,270.00, Used: €0.00)
- Eligible lots gain: Pre-tax €2,755.53 | Est. Post-tax €2,265.31
  ⚠️ 提示: 建议卖出批次收益超出年度免税额，超出部分需缴纳 33% 爱尔兰资本利得税 (CGT)。
  ℹ️ 提示: cgt_used_allowance_eur 需由用户手动维护；系统无法感知本ESPP之外的其他资产交易，此额度需自行核实是否已被其他资产收益占用。

Signal: SELL_WINDOW

Reasons:
- 180-day price percentile: 100.0% (threshold: 85.0%)
- Distance from 180-day high: 0.0% (threshold: -5.0%)
- Current price >= 50-day MA: yes ($275.00 vs $255.35)
- 50-day MA >= 200-day MA: yes ($255.35 vs $232.85)
- Lots with >= 10% gain: 14/20

Execution Guidance:
- 💡 建议分批卖出 (例如先卖出 1/3)，若价格继续创出新高可保留剩余批次继续观察。

Tax Deadline: 税务申报期限提醒: 1月-11月发生的卖出，须于当年12月15日前完成CGT缴税。

This is a relative market/portfolio condition, not a prediction of IBM's future price (Not a price prediction).
No trade was executed.
```

### 4.2 集中度风险独立告警（`CONCENTRATION_ALERT`）
```text
⚠️ IBM POSITION CONCENTRATION ALERT
As of: 2026-09-27 18:00

Total Position Value: €13,375.10 ($14,445.11)
Configured Max Limit: €10,000.00
Excess Amount: €3,375.10

Recommendation:
- ⚠️ 单一标的持仓市值已超过风险上限，建议无视技术择时信号，优先减仓至目标限额以下以控制组合集中度风险。

Tax Deadline: 税务申报期限提醒: 1月-11月发生的卖出，须于当年12月15日前完成CGT缴税。
```

---

## 5. 专家评审要点建议（Review Checklist for Experts）

欢迎各位专家针对以下维度提供指导意见：

1. **爱尔兰 CGT 匹配度**：当前将所有收益按 $33\%$ 预估并统一提供税前/税后数字，结合 €1,270 免税额度，是否已足够满足个人税务规划与申报提示需求？
2. **风控阈值设定**：将“集中度风控（90天冷却）”与“择时止盈（30天冷却）”完全解耦的架构是否符合财富管理实践？
3. **参数鲁棒性**：针对 IBM 这类成熟蓝筹科技股，$180$ 观察日 $85\%$ 分位数、$-5\%$ 高点容差与 $10\%$ 单批次浮盈阈值的组合是否具备合理的触发频次与胜率预期？
