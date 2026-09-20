"""
Delivery Route Planner

Reads deliveries from a CSV, groups them into trips respecting a 10kg
capacity, prioritising urgent (low priority number) deliveries and
clustering by area where possible.
"""

import csv
import sys
from dataclasses import dataclass, field
from typing import List, Tuple

CAPACITY_KG = 10.0
FLOAT_EPSILON = 1e-9  # absorbs binary float error on exact-fit sums


@dataclass
class Delivery:
    id: int
    area: str
    priority: int
    weight: float

    def __str__(self) -> str:
        return f"#{self.id} {self.area} p{self.priority} {self.weight}kg"


@dataclass
class Trip:
    deliveries: List[Delivery] = field(default_factory=list)
    weight: float = 0.0

    def can_fit(self, d: Delivery) -> bool:
        # Epsilon guards against 4.1 + 2.6 + 3.3 == 10.000000000000002
        return self.weight + d.weight <= CAPACITY_KG + FLOAT_EPSILON

    def add(self, d: Delivery) -> None:
        self.deliveries.append(d)
        self.weight += d.weight

    @property
    def areas(self) -> set:
        return {d.area for d in self.deliveries}


def _hr() -> None:
    """Print a 60-character horizontal rule."""
    print("=" * 60)


def load_deliveries(path: str) -> Tuple[List[Delivery], List[Delivery]]:
    """
    Read and validate the input CSV.

    Returns (valid, undeliverable). Rows that are malformed or carry a
    non-positive weight are skipped with a warning on stderr; rows over
    CAPACITY_KG are returned in the undeliverable bucket so the caller
    can report them.
    """
    valid: List[Delivery] = []
    undeliverable: List[Delivery] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"id", "area", "priority", "weight_kg"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(
                f"CSV must contain columns {required}, got {reader.fieldnames}"
            )

        for row_num, row in enumerate(reader, start=2):
            try:
                d = Delivery(
                    id=int(row["id"]),
                    area=row["area"].strip(),
                    priority=int(row["priority"]),
                    weight=float(row["weight_kg"]),
                )
            except (ValueError, KeyError) as e:
                print(
                    f"[warn] skipping malformed row {row_num}: {e}",
                    file=sys.stderr,
                )
                continue

            if not d.area:
                print(
                    f"[warn] delivery {d.id} has no area; skipped",
                    file=sys.stderr,
                )
                continue

            if d.weight > CAPACITY_KG:
                undeliverable.append(d)
            elif d.weight <= 0:
                print(
                    f"[warn] delivery {d.id} has non-positive weight; skipped",
                    file=sys.stderr,
                )
            else:
                valid.append(d)

    return valid, undeliverable


def plan_trips(deliveries: List[Delivery]) -> List[Trip]:
    """
    Greedy, area-aware trip builder.

    Deliveries are sorted by (priority asc, area asc), so urgency is
    respected first and same-priority items cluster by area. Each
    delivery is then placed using three passes:

      1. an open trip that already serves this area and has room
      2. any open trip that has room (capacity-first fallback)
      3. a brand-new trip

    Pass 2 exists so that leftover capacity is not wasted when no
    same-area trip can accept the delivery.
    """
    ordered = sorted(deliveries, key=lambda d: (d.priority, d.area))
    open_trips: List[Trip] = []

    for d in ordered:
        # Pass 1: same-area trip with room.
        target = next(
            (t for t in open_trips if d.area in t.areas and t.can_fit(d)),
            None,
        )
        # Pass 2: any trip with room — avoids leaving gaps.
        if target is None:
            target = next((t for t in open_trips if t.can_fit(d)), None)
        # Pass 3: nothing fits, start a new trip.
        if target is None:
            target = Trip()
            open_trips.append(target)

        target.add(d)

    return open_trips


def print_trip_details(trips: List[Trip], undeliverable: List[Delivery]) -> None:
    """Print every trip and its deliveries, then the undeliverable bucket."""
    _hr()
    print(f"TRIPS ({len(trips)})")
    _hr()

    for i, t in enumerate(trips, 1):
        areas = ", ".join(sorted(t.areas))
        print(f"\nTrip {i}  |  {t.weight:.2f} kg  |  areas: {areas}")
        for d in t.deliveries:
            print(f"   - {d}")

    if undeliverable:
        print()
        _hr()
        print(
            f"UNDELIVERABLE ({len(undeliverable)}) — exceed {CAPACITY_KG:.0f}kg")
        _hr()
        for d in undeliverable:
            print(f"   - {d}")


def print_utilisation_report(trips: List[Trip]) -> None:
    """
    Print a trip-capacity utilisation summary.

    Reports total trips, aggregate stats, and a per-trip breakdown.
    The Min line highlights the most under-filled trip, useful as
    concrete evidence of where the greedy packing left capacity idle.
    """
    if not trips:
        print()
        _hr()
        print("UTILISATION SUMMARY")
        _hr()
        print("  No trips planned — nothing to report.")
        return

    # (percent, trip) pairs, computed once and reused below.
    util = [(t.weight / CAPACITY_KG * 100.0, t) for t in trips]
    total_kg = sum(t.weight for t in trips)
    avg_pct = sum(p for p, _ in util) / len(util)

    # Track indices alongside values so we don't need trips.index(),
    # which would use == and could match the wrong (equal-valued) trip.
    min_idx, (min_pct, min_trip) = min(
        enumerate(util, 1), key=lambda pair: pair[1][0]
    )
    max_idx, (max_pct, max_trip) = max(
        enumerate(util, 1), key=lambda pair: pair[1][0]
    )

    print()
    _hr()
    print("UTILISATION SUMMARY")
    _hr()
    print(f"  Trips:    {len(trips)}")
    print(f"  Total:    {total_kg:.2f} kg moved")
    print(f"  Average:  {avg_pct:5.1f}%")
    print(
        f"  Min:      {min_trip.weight:.2f}/{CAPACITY_KG:.0f} kg "
        f"({min_pct:5.1f}%)  <- Trip {min_idx} (most idle capacity)"
    )
    print(
        f"  Max:      {max_trip.weight:.2f}/{CAPACITY_KG:.0f} kg "
        f"({max_pct:5.1f}%)  <- Trip {max_idx}"
    )

    print("\n  Per-trip breakdown:")
    for i, (pct, t) in enumerate(util, 1):
        areas = ", ".join(sorted(t.areas))
        print(
            f"    Trip {i}: {t.weight:5.2f}/{CAPACITY_KG:.0f} kg "
            f"({pct:5.1f}%)  [{areas}]"
        )


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "deliveries.csv"

    try:
        valid, undeliverable = load_deliveries(path)
    except FileNotFoundError:
        print(f"error: input file not found: {path}", file=sys.stderr)
        sys.exit(1)

    # Short-circuit: nothing to report at all. Avoids printing empty
    # "TRIPS (0)" / "UTILISATION SUMMARY" headers.
    if not valid and not undeliverable:
        print("No deliveries to plan. Exiting cleanly.")
        return

    trips = plan_trips(valid)
    print_trip_details(trips, undeliverable)
    print_utilisation_report(trips)


if __name__ == "__main__":
    main()
