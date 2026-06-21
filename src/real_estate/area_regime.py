from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


AREA_REGIME_DYNAMIC_INFLOW = "Dynamic Inflow Market"
AREA_REGIME_STABLE_PREMIUM = "Stable Premium Residential"
AREA_REGIME_HIGH_CHURN = "High Churn Rental Market"
AREA_REGIME_STABLE = "Stable Residential Market"
AREA_REGIME_AGING_STAGNANT = "Aging / Stagnant Market"
AREA_REGIME_DATA_INSUFFICIENT = "Data Insufficient"

RENTAL_SIGNAL_STRONG = "Strong"
RENTAL_SIGNAL_POSITIVE = "Positive"
RENTAL_SIGNAL_NEUTRAL = "Neutral"
RENTAL_SIGNAL_CAUTION = "Caution"
RENTAL_SIGNAL_WEAK = "Weak"
RENTAL_SIGNAL_DATA_INSUFFICIENT = "Data Insufficient"

LEVEL_HIGH = "high"
LEVEL_MEDIUM = "medium"
LEVEL_LOW = "low"

RENTAL_DEMAND_SIGNAL_ORDER = {
    RENTAL_SIGNAL_STRONG: 0,
    RENTAL_SIGNAL_POSITIVE: 1,
    RENTAL_SIGNAL_NEUTRAL: 2,
    RENTAL_SIGNAL_CAUTION: 3,
    RENTAL_SIGNAL_WEAK: 4,
    RENTAL_SIGNAL_DATA_INSUFFICIENT: 5,
}


@dataclass(frozen=True)
class AreaPopulationSnapshot:
    area_code: str
    area_name: str
    year: int
    month: int | None

    population_total: int | None
    households_total: int | None

    population_japanese: int | None = None
    population_foreign: int | None = None

    population_age_0_19: int | None = None
    population_age_20_39: int | None = None
    population_age_40_64: int | None = None
    population_age_65_plus: int | None = None


@dataclass(frozen=True)
class AreaMigrationFlow:
    area_code: str
    area_name: str
    year: int
    month: int | None

    inflow_total: int | None
    outflow_total: int | None

    inflow_domestic: int | None = None
    outflow_domestic: int | None = None
    inflow_foreign: int | None = None
    outflow_foreign: int | None = None


@dataclass(frozen=True)
class AreaMobilityMetrics:
    area_code: str
    area_name: str
    year: int
    month: int | None

    population_total: int | None
    households_total: int | None

    inflow_total: int | None
    outflow_total: int | None
    net_inflow: int | None

    population_growth_rate: float | None
    household_growth_rate: float | None

    inflow_rate: float | None
    outflow_rate: float | None
    net_inflow_rate: float | None
    population_turnover_rate: float | None

    young_adult_share: float | None
    working_age_share: float | None
    elderly_share: float | None
    foreign_resident_share: float | None

    turnover_level: str | None
    net_inflow_level: str | None
    household_growth_level: str | None

    area_regime: str
    rental_demand_signal: str

    notes: list[str]


@dataclass(frozen=True)
class RealEstateAssetAreaMapping:
    asset_id: str
    asset_name: str
    area_code: str
    area_name: str
    ward_name: str
    station_name: str | None
    layout: str | None
    size_sqm: float | None


USER_ASSET_AREA_MAPPINGS = [
    RealEstateAssetAreaMapping(
        asset_id="kugahara",
        asset_name="大田区 久ヶ原",
        area_code="13111",
        area_name="Ota",
        ward_name="大田区",
        station_name="久が原",
        layout="1LDK",
        size_sqm=45.0,
    ),
    RealEstateAssetAreaMapping(
        asset_id="sasazuka",
        asset_name="渋谷区 笹塚",
        area_code="13113",
        area_name="Shibuya",
        ward_name="渋谷区",
        station_name="笹塚",
        layout="1LDK",
        size_sqm=33.0,
    ),
    RealEstateAssetAreaMapping(
        asset_id="nishi_ikebukuro",
        asset_name="豊島区 西池袋",
        area_code="13116",
        area_name="Toshima",
        ward_name="豊島区",
        station_name="池袋",
        layout="1K",
        size_sqm=25.0,
    ),
    RealEstateAssetAreaMapping(
        asset_id="shirokane_takanawa",
        asset_name="港区 白金高輪",
        area_code="13103",
        area_name="Minato",
        ward_name="港区",
        station_name="白金高輪",
        layout="1K",
        size_sqm=24.0,
    ),
    RealEstateAssetAreaMapping(
        asset_id="azumabashi",
        asset_name="墨田区 吾妻橋",
        area_code="13107",
        area_name="Sumida",
        ward_name="墨田区",
        station_name="本所吾妻橋",
        layout="1LDK",
        size_sqm=40.0,
    ),
    RealEstateAssetAreaMapping(
        asset_id="himonya",
        asset_name="目黒区 碑文谷",
        area_code="13110",
        area_name="Meguro",
        ward_name="目黒区",
        station_name="都立大学",
        layout="1K",
        size_sqm=20.0,
    ),
]


def safe_divide(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def calculate_population_growth_rate(
    current: AreaPopulationSnapshot,
    previous: AreaPopulationSnapshot | None,
) -> float | None:
    if previous is None:
        return None
    difference = _subtract_optional(current.population_total, previous.population_total)
    return safe_divide(difference, previous.population_total)


def calculate_household_growth_rate(
    current: AreaPopulationSnapshot,
    previous: AreaPopulationSnapshot | None,
) -> float | None:
    if previous is None:
        return None
    difference = _subtract_optional(current.households_total, previous.households_total)
    return safe_divide(difference, previous.households_total)


def calculate_area_mobility_metrics(
    current_population: AreaPopulationSnapshot,
    migration_flow: AreaMigrationFlow | None,
    previous_population: AreaPopulationSnapshot | None = None,
) -> AreaMobilityMetrics:
    population_total = current_population.population_total
    households_total = current_population.households_total
    inflow_total = migration_flow.inflow_total if migration_flow else None
    outflow_total = migration_flow.outflow_total if migration_flow else None
    net_inflow = _subtract_optional(inflow_total, outflow_total)

    age_20_64 = _sum_optional(
        current_population.population_age_20_39,
        current_population.population_age_40_64,
    )

    notes = _build_base_notes(
        population_total=population_total,
        households_total=households_total,
        inflow_total=inflow_total,
        outflow_total=outflow_total,
        previous_population=previous_population,
    )

    return AreaMobilityMetrics(
        area_code=current_population.area_code,
        area_name=current_population.area_name,
        year=current_population.year,
        month=current_population.month,
        population_total=population_total,
        households_total=households_total,
        inflow_total=inflow_total,
        outflow_total=outflow_total,
        net_inflow=net_inflow,
        population_growth_rate=calculate_population_growth_rate(
            current_population,
            previous_population,
        ),
        household_growth_rate=calculate_household_growth_rate(
            current_population,
            previous_population,
        ),
        inflow_rate=safe_divide(inflow_total, population_total),
        outflow_rate=safe_divide(outflow_total, population_total),
        net_inflow_rate=safe_divide(net_inflow, population_total),
        population_turnover_rate=safe_divide(
            _sum_optional(inflow_total, outflow_total),
            population_total,
        ),
        young_adult_share=safe_divide(
            current_population.population_age_20_39,
            population_total,
        ),
        working_age_share=safe_divide(age_20_64, population_total),
        elderly_share=safe_divide(
            current_population.population_age_65_plus,
            population_total,
        ),
        foreign_resident_share=safe_divide(
            current_population.population_foreign,
            population_total,
        ),
        turnover_level=None,
        net_inflow_level=None,
        household_growth_level=None,
        area_regime=AREA_REGIME_DATA_INSUFFICIENT,
        rental_demand_signal=RENTAL_SIGNAL_DATA_INSUFFICIENT,
        notes=notes,
    )


def assign_relative_levels(
    metrics_list: list[AreaMobilityMetrics],
) -> list[AreaMobilityMetrics]:
    turnover_levels = _relative_level_by_area_code(
        metrics_list,
        "population_turnover_rate",
    )
    net_inflow_levels = _relative_level_by_area_code(metrics_list, "net_inflow_rate")
    household_growth_levels = _relative_level_by_area_code(
        metrics_list,
        "household_growth_rate",
    )

    return [
        replace(
            metrics,
            turnover_level=turnover_levels.get(metrics.area_code),
            net_inflow_level=net_inflow_levels.get(metrics.area_code),
            household_growth_level=household_growth_levels.get(metrics.area_code),
        )
        for metrics in metrics_list
    ]


def classify_area_regime(metrics: AreaMobilityMetrics) -> str:
    if _missing_required_for_regime(metrics):
        return AREA_REGIME_DATA_INSUFFICIENT

    if (
        metrics.population_growth_rate is not None
        and metrics.population_growth_rate < 0
        and _is_negative_or_flat(metrics.household_growth_rate)
        and _is_negative(metrics.net_inflow_rate)
        and metrics.turnover_level == LEVEL_LOW
        and _is_high_elderly_share(metrics)
    ):
        return AREA_REGIME_AGING_STAGNANT

    if (
        metrics.turnover_level == LEVEL_HIGH
        and _is_positive(metrics.net_inflow_rate)
        and _is_positive(metrics.household_growth_rate)
    ):
        return AREA_REGIME_DYNAMIC_INFLOW

    if (
        metrics.turnover_level == LEVEL_HIGH
        and _is_flat_or_slightly_negative(metrics.net_inflow_rate)
        and _is_high_young_adult_share(metrics)
    ):
        return AREA_REGIME_HIGH_CHURN

    if (
        metrics.turnover_level in {LEVEL_LOW, LEVEL_MEDIUM}
        and _is_positive_or_flat(metrics.net_inflow_rate)
        and _is_positive_or_flat(metrics.household_growth_rate)
    ):
        return AREA_REGIME_STABLE_PREMIUM

    if (
        metrics.turnover_level in {LEVEL_LOW, LEVEL_MEDIUM}
        and _is_flat(metrics.net_inflow_rate)
        and _is_positive_or_flat(metrics.household_growth_rate)
    ):
        return AREA_REGIME_STABLE

    if _is_negative(metrics.net_inflow_rate) or _is_negative(
        metrics.household_growth_rate,
    ):
        return AREA_REGIME_AGING_STAGNANT

    return AREA_REGIME_STABLE


def classify_rental_demand_signal(metrics: AreaMobilityMetrics) -> str:
    if _missing_required_for_rental_signal(metrics):
        return RENTAL_SIGNAL_DATA_INSUFFICIENT

    if (
        metrics.turnover_level == LEVEL_HIGH
        and _is_positive(metrics.net_inflow_rate)
        and _is_positive(metrics.household_growth_rate)
        and _is_high_young_adult_share(metrics)
    ):
        return RENTAL_SIGNAL_STRONG

    if (
        metrics.turnover_level in {LEVEL_MEDIUM, LEVEL_HIGH}
        and _is_positive_or_flat(metrics.net_inflow_rate)
        and _is_positive(metrics.household_growth_rate)
    ):
        return RENTAL_SIGNAL_POSITIVE

    if (
        _is_negative(metrics.population_growth_rate)
        and _is_negative(metrics.household_growth_rate)
        and metrics.turnover_level == LEVEL_LOW
        and _is_high_elderly_share(metrics)
    ):
        return RENTAL_SIGNAL_WEAK

    if _is_negative(metrics.net_inflow_rate) or (
        metrics.turnover_level == LEVEL_HIGH
        and not _is_positive(metrics.net_inflow_rate)
    ):
        return RENTAL_SIGNAL_CAUTION

    if (
        _is_positive_or_flat(metrics.population_growth_rate)
        and _is_positive_or_flat(metrics.household_growth_rate)
        and metrics.turnover_level == LEVEL_MEDIUM
    ):
        return RENTAL_SIGNAL_NEUTRAL

    return RENTAL_SIGNAL_NEUTRAL


def calculate_area_regime_batch(
    population_snapshots: list[AreaPopulationSnapshot],
    migration_flows: list[AreaMigrationFlow],
    previous_population_snapshots: list[AreaPopulationSnapshot] | None = None,
) -> list[AreaMobilityMetrics]:
    migration_by_key = {
        _area_period_key(flow.area_code, flow.year, flow.month): flow
        for flow in migration_flows
    }
    previous_by_area = {
        snapshot.area_code: snapshot
        for snapshot in previous_population_snapshots or []
    }

    base_metrics = [
        calculate_area_mobility_metrics(
            current_population=snapshot,
            migration_flow=migration_by_key.get(
                _area_period_key(snapshot.area_code, snapshot.year, snapshot.month),
            ),
            previous_population=previous_by_area.get(snapshot.area_code),
        )
        for snapshot in population_snapshots
    ]

    leveled_metrics = assign_relative_levels(base_metrics)
    classified_metrics = [
        _with_classification_notes(
            replace(
                metrics,
                area_regime=classify_area_regime(metrics),
                rental_demand_signal=classify_rental_demand_signal(metrics),
            ),
        )
        for metrics in leveled_metrics
    ]
    return sorted(classified_metrics, key=lambda metrics: (metrics.area_name, metrics.area_code))


def area_metrics_to_dict(metrics: AreaMobilityMetrics) -> dict[str, Any]:
    return asdict(metrics)


def rank_by_turnover(
    metrics_list: list[AreaMobilityMetrics],
) -> list[AreaMobilityMetrics]:
    return sorted(
        metrics_list,
        key=lambda metrics: _sort_float_desc(metrics.population_turnover_rate),
    )


def rank_by_net_inflow(
    metrics_list: list[AreaMobilityMetrics],
) -> list[AreaMobilityMetrics]:
    return sorted(
        metrics_list,
        key=lambda metrics: _sort_float_desc(metrics.net_inflow_rate),
    )


def rank_by_rental_demand(
    metrics_list: list[AreaMobilityMetrics],
) -> list[AreaMobilityMetrics]:
    return sorted(
        metrics_list,
        key=lambda metrics: (
            RENTAL_DEMAND_SIGNAL_ORDER.get(
                metrics.rental_demand_signal,
                RENTAL_DEMAND_SIGNAL_ORDER[RENTAL_SIGNAL_DATA_INSUFFICIENT],
            ),
            metrics.area_name,
        ),
    )


def generate_area_interpretation(metrics: AreaMobilityMetrics) -> str:
    area_name = metrics.area_name

    if metrics.area_regime == AREA_REGIME_DATA_INSUFFICIENT:
        return (
            f"{area_name} does not have enough population, migration, or household data "
            "to classify area regime and rental demand signal."
        )

    if metrics.rental_demand_signal == RENTAL_SIGNAL_CAUTION:
        return (
            f"{area_name} has high turnover but weak or negative net inflow. "
            "This may indicate a transient market with frequent resident replacement. "
            "Rental demand may exist, but vacancy cycle and rent stability should be watched."
        )

    if metrics.rental_demand_signal == RENTAL_SIGNAL_WEAK:
        return (
            f"{area_name} shows weak demographic momentum, low liquidity, and a high elderly share. "
            "This may weigh on long-term residential demand, rent growth, and exit liquidity. "
            f"This area is classified as {metrics.area_regime} with {metrics.rental_demand_signal} rental demand signal."
        )

    mobility_text = _mobility_interpretation(metrics)
    young_adult_text = (
        " The young adult share is also high, which may support 1K and 1LDK rental demand."
        if _is_high_young_adult_share(metrics)
        else ""
    )
    return (
        f"{area_name} {mobility_text}"
        f"{young_adult_text} "
        f"This area is classified as {metrics.area_regime} with {metrics.rental_demand_signal} rental demand signal."
    )


def summarize_asset_area_exposure(
    metrics_list: list[AreaMobilityMetrics],
    asset_mappings: list[RealEstateAssetAreaMapping],
) -> list[dict[str, Any]]:
    metrics_by_area_code = {metrics.area_code: metrics for metrics in metrics_list}
    summaries: list[dict[str, Any]] = []

    for asset in asset_mappings:
        metrics = metrics_by_area_code.get(asset.area_code)
        if metrics is None:
            summaries.append(
                {
                    "asset_id": asset.asset_id,
                    "asset_name": asset.asset_name,
                    "ward_name": asset.ward_name,
                    "area_regime": AREA_REGIME_DATA_INSUFFICIENT,
                    "rental_demand_signal": RENTAL_SIGNAL_DATA_INSUFFICIENT,
                    "population_turnover_rate": None,
                    "net_inflow_rate": None,
                    "interpretation": "The asset area could not be matched to ward-level market regime data.",
                },
            )
            continue

        summaries.append(
            {
                "asset_id": asset.asset_id,
                "asset_name": asset.asset_name,
                "ward_name": asset.ward_name,
                "area_regime": metrics.area_regime,
                "rental_demand_signal": metrics.rental_demand_signal,
                "population_turnover_rate": metrics.population_turnover_rate,
                "net_inflow_rate": metrics.net_inflow_rate,
                "interpretation": _asset_area_interpretation(metrics),
            },
        )

    return summaries


def load_population_snapshots_csv(path: str | Path) -> list[AreaPopulationSnapshot]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return [
            AreaPopulationSnapshot(
                area_code=row["area_code"],
                area_name=row["area_name"],
                year=_parse_required_int(row["year"], "year"),
                month=_parse_optional_int(row.get("month")),
                population_total=_parse_optional_int(row.get("population_total")),
                households_total=_parse_optional_int(row.get("households_total")),
                population_japanese=_parse_optional_int(row.get("population_japanese")),
                population_foreign=_parse_optional_int(row.get("population_foreign")),
                population_age_0_19=_parse_optional_int(row.get("population_age_0_19")),
                population_age_20_39=_parse_optional_int(row.get("population_age_20_39")),
                population_age_40_64=_parse_optional_int(row.get("population_age_40_64")),
                population_age_65_plus=_parse_optional_int(row.get("population_age_65_plus")),
            )
            for row in csv.DictReader(file)
        ]


def load_migration_flows_csv(path: str | Path) -> list[AreaMigrationFlow]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return [
            AreaMigrationFlow(
                area_code=row["area_code"],
                area_name=row["area_name"],
                year=_parse_required_int(row["year"], "year"),
                month=_parse_optional_int(row.get("month")),
                inflow_total=_parse_optional_int(row.get("inflow_total")),
                outflow_total=_parse_optional_int(row.get("outflow_total")),
                inflow_domestic=_parse_optional_int(row.get("inflow_domestic")),
                outflow_domestic=_parse_optional_int(row.get("outflow_domestic")),
                inflow_foreign=_parse_optional_int(row.get("inflow_foreign")),
                outflow_foreign=_parse_optional_int(row.get("outflow_foreign")),
            )
            for row in csv.DictReader(file)
        ]


def _subtract_optional(
    left: int | float | None,
    right: int | float | None,
) -> int | float | None:
    if left is None or right is None:
        return None
    return left - right


def _sum_optional(*values: int | float | None) -> int | float | None:
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _build_base_notes(
    population_total: int | None,
    households_total: int | None,
    inflow_total: int | None,
    outflow_total: int | None,
    previous_population: AreaPopulationSnapshot | None,
) -> list[str]:
    notes: list[str] = []
    if population_total is None:
        notes.append("Population total is missing")
    if households_total is None:
        notes.append("Households total is missing")
    if inflow_total is None:
        notes.append("Inflow total is missing")
    if outflow_total is None:
        notes.append("Outflow total is missing")
    if previous_population is None:
        notes.append("Previous population snapshot is missing")
    return notes


def _relative_level_by_area_code(
    metrics_list: list[AreaMobilityMetrics],
    attribute_name: str,
) -> dict[str, str]:
    values = sorted(
        getattr(metrics, attribute_name)
        for metrics in metrics_list
        if getattr(metrics, attribute_name) is not None
    )
    if not values:
        return {}

    q1 = _percentile_nearest_rank(values, 0.25)
    q3 = _percentile_nearest_rank(values, 0.75)
    levels: dict[str, str] = {}
    for metrics in metrics_list:
        value = getattr(metrics, attribute_name)
        if value is None:
            continue
        if value >= q3:
            levels[metrics.area_code] = LEVEL_HIGH
        elif value <= q1:
            levels[metrics.area_code] = LEVEL_LOW
        else:
            levels[metrics.area_code] = LEVEL_MEDIUM
    return levels


def _percentile_nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    index = round((len(values) - 1) * percentile)
    return values[index]


def _with_classification_notes(metrics: AreaMobilityMetrics) -> AreaMobilityMetrics:
    notes = list(metrics.notes)

    if metrics.turnover_level == LEVEL_HIGH:
        notes.append("High population turnover")
    elif metrics.turnover_level == LEVEL_LOW:
        notes.append("Low population turnover")

    if _is_positive(metrics.net_inflow_rate):
        notes.append("Positive net inflow")
    elif _is_negative(metrics.net_inflow_rate):
        notes.append("Negative net inflow")

    if _is_positive(metrics.household_growth_rate):
        notes.append("Positive household growth")
    elif _is_negative(metrics.household_growth_rate):
        notes.append("Negative household growth")

    if _is_high_young_adult_share(metrics):
        notes.append("Young adult share is high")
    if _is_high_elderly_share(metrics):
        notes.append("Elderly share is high")

    return replace(metrics, notes=notes)


def _missing_required_for_regime(metrics: AreaMobilityMetrics) -> bool:
    return any(
        value is None
        for value in [
            metrics.population_total,
            metrics.households_total,
            metrics.population_turnover_rate,
            metrics.net_inflow_rate,
            metrics.household_growth_rate,
            metrics.turnover_level,
        ]
    )


def _missing_required_for_rental_signal(metrics: AreaMobilityMetrics) -> bool:
    return _missing_required_for_regime(metrics)


def _is_positive(value: float | None) -> bool:
    return value is not None and value > 0


def _is_negative(value: float | None) -> bool:
    return value is not None and value < 0


def _is_flat(value: float | None) -> bool:
    return value is not None and abs(value) <= 0.001


def _is_positive_or_flat(value: float | None) -> bool:
    return value is not None and value >= -0.001


def _is_negative_or_flat(value: float | None) -> bool:
    return value is not None and value <= 0.001


def _is_flat_or_slightly_negative(value: float | None) -> bool:
    return value is not None and -0.005 <= value <= 0.001


def _is_high_young_adult_share(metrics: AreaMobilityMetrics) -> bool:
    if metrics.young_adult_share is None:
        return False
    return metrics.young_adult_share >= 0.30


def _is_high_elderly_share(metrics: AreaMobilityMetrics) -> bool:
    if metrics.elderly_share is None:
        return False
    return metrics.elderly_share >= 0.25


def _mobility_interpretation(metrics: AreaMobilityMetrics) -> str:
    if metrics.turnover_level == LEVEL_HIGH and _is_positive(metrics.net_inflow_rate):
        return (
            "shows high population turnover and positive net inflow. "
            "This suggests strong area liquidity and continuous residential demand."
        )
    if metrics.turnover_level == LEVEL_LOW and _is_positive_or_flat(metrics.net_inflow_rate):
        return (
            "shows relatively stable population movement with positive or flat net inflow. "
            "This suggests stable residential preference rather than high churn."
        )
    if _is_negative(metrics.net_inflow_rate):
        return (
            "shows negative net inflow. "
            "This suggests residential demand should be monitored carefully."
        )
    return (
        "shows broadly stable demographic conditions. "
        "This suggests steady rental demand with limited upside signal."
    )


def _asset_area_interpretation(metrics: AreaMobilityMetrics) -> str:
    if metrics.rental_demand_signal == RENTAL_SIGNAL_STRONG:
        return "The asset is located in an area with strong population mobility and positive net inflow."
    if metrics.rental_demand_signal == RENTAL_SIGNAL_POSITIVE:
        return "The asset is located in an area with positive demographic demand signals."
    if metrics.rental_demand_signal == RENTAL_SIGNAL_CAUTION:
        return "The asset is located in an area where churn exists, but net inflow or household growth should be watched."
    if metrics.rental_demand_signal == RENTAL_SIGNAL_WEAK:
        return "The asset is located in an area with weak demographic demand signals."
    if metrics.rental_demand_signal == RENTAL_SIGNAL_DATA_INSUFFICIENT:
        return "The asset area does not have enough data for a reliable regime classification."
    return "The asset is located in an area with stable but not strongly growing residential demand."


def _sort_float_desc(value: float | None) -> tuple[int, float]:
    if value is None:
        return (1, 0.0)
    return (0, -value)


def _area_period_key(
    area_code: str,
    year: int,
    month: int | None,
) -> tuple[str, int, int | None]:
    return (area_code, year, month)


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _parse_required_int(value: str, field_name: str) -> int:
    if value == "":
        raise ValueError(f"{field_name} is required")
    return int(value)
