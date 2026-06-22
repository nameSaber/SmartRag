def test_dependency_health_reports_degraded_when_external_services_down(monkeypatch):
    from app.integrations import health

    monkeypatch.setattr(health, "check_mysql_url", lambda: health.DependencyStatus("mysql", "UP"))
    monkeypatch.setattr(health, "check_redis", lambda: health.DependencyStatus("redis", "DOWN", "missing"))
    monkeypatch.setattr(health, "check_elasticsearch", lambda: health.DependencyStatus("elasticsearch", "UP"))
    monkeypatch.setattr(health, "check_kafka", lambda: health.DependencyStatus("kafka", "UP"))
    monkeypatch.setattr(health, "check_minio", lambda: health.DependencyStatus("minio", "UP"))

    result = health.dependency_health()

    assert result["status"] == "DEGRADED"
    assert result["dependencies"]["redis"]["message"] == "missing"
