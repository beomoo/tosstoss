from sqlalchemy import text


def test_sqlite_metadata_repository_roundtrips(database_context) -> None:
    securities = database_context.metadata.list_securities()
    assert [item.security_id for item in securities] == [
        "security_kr_synthetic_common",
        "security_us_synthetic_common",
    ]
    assert database_context.metadata.issuer_exists("issuer_kr_synthetic") is True
    assert database_context.metadata.issuer_exists("issuer_missing") is False
    with database_context.engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0005_phase_02_cp3_c2_b_issuer_authority"
        )
    assert database_context.metadata.database_revision() == "0001_phase_01"
    assert database_context.metadata.fixture_version() == "0.1.0"
    assert (
        database_context.metadata.fixture_manifest_digest()
        == database_context.analytics.manifest_digest
    )


def test_analytics_repository_keeps_missing_as_null(database_context) -> None:
    overview = database_context.analytics.company_overview("issuer_kr_synthetic")
    assert overview is not None
    eps = next(item for item in overview.financial_facts if item.account_code == "EarningsPerShare")
    assert eps.value is None
    assert eps.missing_reasons["value"] == "UNAVAILABLE"
