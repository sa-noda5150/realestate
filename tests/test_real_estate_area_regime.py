from src.real_estate.area_regime import (
    AREA_REGIME_DYNAMIC_INFLOW,
    AREA_REGIME_HIGH_CHURN,
    RENTAL_SIGNAL_CAUTION,
    RENTAL_SIGNAL_STRONG,
    AreaMigrationFlow,
    AreaMobilityMetrics,
    AreaPopulationSnapshot,
    RealEstateAssetAreaMapping,
    calculate_area_mobility_metrics,
    calculate_area_regime_batch,
    classify_area_regime,
    classify_rental_demand_signal,
    generate_area_interpretation,
    rank_by_rental_demand,
    safe_divide,
    summarize_asset_area_exposure,
)


def test_safe_divide() -> None:
    assert safe_divide(10, 2) == 5
    assert safe_divide(10, 0) is None
    assert safe_divide(None, 10) is None
    assert safe_divide(10, None) is None


def test_turnover_calculation() -> None:
    metrics = calculate_area_mobility_metrics(
        current_population=AreaPopulationSnapshot(
            area_code="13113",
            area_name="Shibuya",
            year=2024,
            month=None,
            population_total=100_000,
            households_total=60_000,
        ),
        migration_flow=AreaMigrationFlow(
            area_code="13113",
            area_name="Shibuya",
            year=2024,
            month=None,
            inflow_total=8_000,
            outflow_total=7_000,
        ),
    )

    assert metrics.population_turnover_rate == 0.15
    assert metrics.net_inflow == 1_000
    assert metrics.net_inflow_rate == 0.01


def test_dynamic_inflow_classification() -> None:
    metrics = _metrics(
        turnover_level="high",
        net_inflow_rate=0.01,
        household_growth_rate=0.01,
    )

    assert classify_area_regime(metrics) == AREA_REGIME_DYNAMIC_INFLOW


def test_high_churn_classification() -> None:
    metrics = _metrics(
        turnover_level="high",
        net_inflow_rate=-0.002,
        household_growth_rate=0.002,
        young_adult_share=0.35,
    )

    assert classify_area_regime(metrics) == AREA_REGIME_HIGH_CHURN
    assert classify_rental_demand_signal(metrics) == RENTAL_SIGNAL_CAUTION


def test_batch_assigns_levels_and_classifies() -> None:
    current = [
        AreaPopulationSnapshot("13101", "Chiyoda", 2024, None, 68_500, 39_000, population_age_20_39=21_000, population_age_40_64=26_000, population_age_65_plus=12_500),
        AreaPopulationSnapshot("13102", "Chuo", 2024, None, 180_000, 105_000, population_age_20_39=62_000, population_age_40_64=70_000, population_age_65_plus=20_000),
        AreaPopulationSnapshot("13113", "Shibuya", 2024, None, 230_000, 145_000, population_age_20_39=82_800, population_age_40_64=83_000, population_age_65_plus=38_000),
        AreaPopulationSnapshot("13120", "Nerima", 2024, None, 735_000, 385_000, population_age_20_39=160_000, population_age_40_64=270_000, population_age_65_plus=180_000),
    ]
    previous = [
        AreaPopulationSnapshot("13101", "Chiyoda", 2023, None, 67_900, 38_800),
        AreaPopulationSnapshot("13102", "Chuo", 2023, None, 177_000, 101_000),
        AreaPopulationSnapshot("13113", "Shibuya", 2023, None, 228_000, 143_000),
        AreaPopulationSnapshot("13120", "Nerima", 2023, None, 736_000, 386_000),
    ]
    flows = [
        AreaMigrationFlow("13101", "Chiyoda", 2024, None, 8_500, 7_600),
        AreaMigrationFlow("13102", "Chuo", 2024, None, 24_000, 18_000),
        AreaMigrationFlow("13113", "Shibuya", 2024, None, 34_000, 30_000),
        AreaMigrationFlow("13120", "Nerima", 2024, None, 28_000, 30_000),
    ]

    results = calculate_area_regime_batch(current, flows, previous)
    shibuya = next(metrics for metrics in results if metrics.area_code == "13113")

    assert shibuya.turnover_level == "high"
    assert shibuya.net_inflow_level == "high"
    assert shibuya.rental_demand_signal == RENTAL_SIGNAL_STRONG


def test_rank_by_rental_demand_orders_signals() -> None:
    caution = _metrics(area_name="Caution", rental_demand_signal="Caution")
    strong = _metrics(area_name="Strong", rental_demand_signal="Strong")

    assert rank_by_rental_demand([caution, strong]) == [strong, caution]


def test_generate_area_interpretation() -> None:
    metrics = _metrics(
        area_name="Shibuya",
        area_regime=AREA_REGIME_DYNAMIC_INFLOW,
        rental_demand_signal=RENTAL_SIGNAL_STRONG,
        turnover_level="high",
        net_inflow_rate=0.01,
        young_adult_share=0.36,
    )

    interpretation = generate_area_interpretation(metrics)

    assert "Shibuya shows high population turnover and positive net inflow" in interpretation
    assert "1K and 1LDK" in interpretation


def test_summarize_asset_area_exposure() -> None:
    metrics = _metrics(
        area_code="13113",
        area_name="Shibuya",
        area_regime=AREA_REGIME_DYNAMIC_INFLOW,
        rental_demand_signal=RENTAL_SIGNAL_STRONG,
        population_turnover_rate=0.278,
        net_inflow_rate=0.017,
    )
    asset = RealEstateAssetAreaMapping(
        asset_id="sasazuka",
        asset_name="渋谷区 笹塚",
        area_code="13113",
        area_name="Shibuya",
        ward_name="渋谷区",
        station_name="笹塚",
        layout="1LDK",
        size_sqm=33.0,
    )

    summary = summarize_asset_area_exposure([metrics], [asset])

    assert summary[0]["asset_id"] == "sasazuka"
    assert summary[0]["area_regime"] == AREA_REGIME_DYNAMIC_INFLOW
    assert "strong population mobility" in summary[0]["interpretation"]


def _metrics(
    area_code: str = "13113",
    area_name: str = "Shibuya",
    turnover_level: str | None = "medium",
    net_inflow_rate: float | None = 0.0,
    household_growth_rate: float | None = 0.0,
    young_adult_share: float | None = 0.30,
    area_regime: str = "Stable Residential Market",
    rental_demand_signal: str = "Neutral",
    population_turnover_rate: float | None = 0.15,
) -> AreaMobilityMetrics:
    return AreaMobilityMetrics(
        area_code=area_code,
        area_name=area_name,
        year=2024,
        month=None,
        population_total=100_000,
        households_total=60_000,
        inflow_total=8_000,
        outflow_total=7_000,
        net_inflow=1_000,
        population_growth_rate=0.0,
        household_growth_rate=household_growth_rate,
        inflow_rate=0.08,
        outflow_rate=0.07,
        net_inflow_rate=net_inflow_rate,
        population_turnover_rate=population_turnover_rate,
        young_adult_share=young_adult_share,
        working_age_share=0.65,
        elderly_share=0.2,
        foreign_resident_share=0.08,
        turnover_level=turnover_level,
        net_inflow_level="medium",
        household_growth_level="medium",
        area_regime=area_regime,
        rental_demand_signal=rental_demand_signal,
        notes=[],
    )
