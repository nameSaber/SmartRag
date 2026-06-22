def test_database_name_from_mysql_url():
    from app.tools.ensure_database import database_name_from_url, root_mysql_url

    url = "mysql+pymysql://root:pass@localhost:3306/pai_smart_fastapi?charset=utf8mb4"

    assert database_name_from_url(url) == "pai_smart_fastapi"
    root_url = root_mysql_url(url)
    assert root_url.database is None
    assert root_url.password == "pass"


def test_database_name_ignored_for_sqlite():
    from app.tools.ensure_database import database_name_from_url

    assert database_name_from_url("sqlite:///:memory:") is None
