from __future__ import annotations

from pathlib import Path
from typing import Any

from src.real_estate.area_regime import (
    area_metrics_to_dict,
    calculate_area_regime_batch,
    generate_area_interpretation,
    load_migration_flows_csv,
    load_population_snapshots_csv,
    rank_by_net_inflow,
    rank_by_rental_demand,
    rank_by_turnover,
)


TABLE_COLUMNS = [
    "area_name",
    "population_total",
    "households_total",
    "inflow_total",
    "outflow_total",
    "net_inflow",
    "population_turnover_rate",
    "net_inflow_rate",
    "household_growth_rate",
    "young_adult_share",
    "foreign_resident_share",
    "area_regime",
    "rental_demand_signal",
]

PERCENTAGE_COLUMNS = [
    "population_turnover_rate",
    "net_inflow_rate",
    "household_growth_rate",
    "young_adult_share",
    "foreign_resident_share",
]


def page_real_estate_area_regime() -> None:
    import streamlit as st

    st.title("Real Estate Area Regime")

    data_dir = Path(__file__).resolve().parents[1] / "data" / "real_estate"
    current_population_path = data_dir / "tokyo_23_population.csv"
    previous_population_path = data_dir / "tokyo_23_population_previous.csv"
    migration_path = data_dir / "tokyo_23_migration.csv"

    try:
        current_population = load_population_snapshots_csv(current_population_path)
        previous_population = load_population_snapshots_csv(previous_population_path)
        migration_flows = load_migration_flows_csv(migration_path)
        metrics = calculate_area_regime_batch(
            population_snapshots=current_population,
            migration_flows=migration_flows,
            previous_population_snapshots=previous_population,
        )
    except FileNotFoundError as error:
        st.error(f"Data file not found: {error.filename}")
        return

    st.success(
        f"Loaded {len(current_population)} population rows and {len(migration_flows)} migration rows.",
    )

    rows = [_format_row(area_metrics_to_dict(item)) for item in metrics]
    st.subheader("Tokyo 23 ward area metrics")
    st.dataframe(rows, use_container_width=True)

    st.subheader("Ranking by population turnover rate")
    st.dataframe(
        [_format_row(area_metrics_to_dict(item)) for item in rank_by_turnover(metrics)][
            :10
        ],
        use_container_width=True,
    )

    st.subheader("Ranking by net inflow rate")
    st.dataframe(
        [_format_row(area_metrics_to_dict(item)) for item in rank_by_net_inflow(metrics)][
            :10
        ],
        use_container_width=True,
    )

    st.subheader("Ranking by rental demand signal")
    st.dataframe(
        [
            _format_row(area_metrics_to_dict(item))
            for item in rank_by_rental_demand(metrics)
        ],
        use_container_width=True,
    )

    area_names = [item.area_name for item in metrics]
    selected_area_name = st.selectbox("Selected area detail", area_names)
    selected_metrics = next(item for item in metrics if item.area_name == selected_area_name)

    st.subheader(f"Area: {selected_metrics.area_name}")
    st.markdown(f"**Area Regime:** {selected_metrics.area_regime}")
    st.markdown(f"**Rental Demand Signal:** {selected_metrics.rental_demand_signal}")
    st.markdown("**Interpretation:**")
    st.write(generate_area_interpretation(selected_metrics))


def _format_row(row: dict[str, Any]) -> dict[str, Any]:
    formatted = {key: row.get(key) for key in TABLE_COLUMNS}
    for column in PERCENTAGE_COLUMNS:
        if formatted[column] is not None:
            formatted[column] = f"{formatted[column]:.1%}"
    return formatted


if __name__ == "__main__":
    page_real_estate_area_regime()
