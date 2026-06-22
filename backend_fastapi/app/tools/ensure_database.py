from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL

from app.core.config import settings


def database_name_from_url(database_url: str) -> str | None:
    url = make_url(database_url)
    if not url.drivername.startswith("mysql"):
        return None
    return url.database


def root_mysql_url(database_url: str) -> URL:
    url = make_url(database_url)
    # URL 转字符串会默认隐藏密码，启动脚本需要保留真实密码连接 MySQL。
    return url._replace(database=None)


def ensure_database_exists() -> None:
    database_name = database_name_from_url(settings.database_url)
    if not database_name:
        return

    import pymysql

    root_url = root_mysql_url(settings.database_url)
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
