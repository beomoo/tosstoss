def test_sample_analysis_packet_has_versioned_extension_points(api_client) -> None:
    response = api_client.get("/api/v1/sample/analysis-packet")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_mode"] == "FIXTURE"
    packet = payload["data"]
    assert packet["result_status"] == "SAMPLE_RESULT"
    assert packet["extensions"]["extension_version"] == "0.1.0"
    assert packet["extensions"]["hypotheses"] == []
    assert packet["extensions"]["invalidation_conditions"] == []
    assert packet["extensions"]["scenario_probability_changes"] == []
