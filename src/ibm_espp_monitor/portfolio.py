import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class EsppLot:
    allocation_date: date
    instrument: str
    contribution_type: str
    cost_basis_usd: Decimal
    quantity: Decimal
    available_from: date

    @property
    def cost_value_usd(self) -> Decimal:
        return self.cost_basis_usd * self.quantity


def load_lots(path: str | Path) -> list[EsppLot]:
    lots: list[EsppLot] = []
    with Path(path).open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            lots.append(
                EsppLot(
                    allocation_date=date.fromisoformat(row["allocation_date"].strip()),
                    instrument=row["instrument"].strip(),
                    contribution_type=row["contribution_type"].strip(),
                    cost_basis_usd=Decimal(row["cost_basis_usd"].strip()),
                    quantity=Decimal(row["quantity"].strip()),
                    available_from=date.fromisoformat(row["available_from"].strip()),
                )
            )
    return lots


def total_quantity(lots: Sequence[EsppLot]) -> Decimal:
    return sum((lot.quantity for lot in lots), Decimal("0"))


def weighted_average_cost_basis(lots: Sequence[EsppLot]) -> Decimal:
    quantity = total_quantity(lots)
    if quantity == Decimal("0"):
        raise ValueError("Cannot calculate average cost for an empty portfolio")
    return sum((lot.cost_value_usd for lot in lots), Decimal("0")) / quantity


def lot_gain(lot: EsppLot, market_price_usd: Decimal) -> Decimal:
    if lot.cost_basis_usd <= Decimal("0"):
        raise ValueError("Cost basis must be positive")
    return (market_price_usd - lot.cost_basis_usd) / lot.cost_basis_usd
