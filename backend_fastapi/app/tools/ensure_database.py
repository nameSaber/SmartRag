from sqlalchemy.engine import make_url

from app.core.config import settings


def database_name_from_url(database_url: str) -> str | None:
    url = make_url(database_url)
    if not url.drivername.startswith("mysql"):
        return None
    return url.database


def root_mysql_url(database_url: str) -> str:
    url = make_url(database_url)
    return str(url.set(database=None))


def ensure_database_exists() -> None:
    database_name = database_name_from_url(settings.database_url)
    if not database_name:
        return

    import pymysql

    root_url = make_url(root_mysql_url(settings.database_url))
    connection = pymysql.connect(
        host=root_url.host or "localhost",
        port=root_url.port or 3306,
        user=root_url.username,
        password=root_url.password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            # 只创建缺失数据库，不修改或删除已有数据。
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()


def main() -> None:
    ensure_database_exists()


if __name__ == "__main__":
    main()

