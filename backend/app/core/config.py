"""分层配置：环境变量 → .env 文件 → 默认值。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DB_URLS = {
    "sqlite": "sqlite:///./vulnscope.db",
    "mysql": "mysql+pymysql://vulnscope:vulnscope@127.0.0.1:3306/vulnscope?charset=utf8mb4",
}


class Settings(BaseSettings):
    """应用全局配置。

    所有配置项均可通过环境变量覆盖，前缀为 `VULNSCOPE_`。
    例如 `VULNSCOPE_DB_BACKEND=mysql` 即可切换数据库后端。

    Attributes:
        APP_NAME: 应用名称。
        APP_ENV: 运行环境，取值 dev / test / prod。
        DB_BACKEND: 数据库后端，sqlite 或 mysql。
        CACHE_BACKEND: 缓存后端，inproc 或 redis（v2 引入）。
        SECRET_KEY: JWT 签名密钥，生产环境务必更换为 32 字节以上随机字符串。
    """

    model_config = SettingsConfigDict(
        env_prefix="VULNSCOPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "VulnScope"
    APP_ENV: str = "dev"  # dev / test / prod
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # 日志（控制台文本 + 文件 JSON，见 app/core/logging.py）
    LOG_LEVEL: str = "INFO"  # DEBUG / INFO / WARNING / ERROR

    # 数据库
    DB_BACKEND: str = "sqlite"
    DATABASE_URL: str | None = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 3600

    # 缓存
    CACHE_BACKEND: str = "inproc"
    CACHE_TTL_SECONDS: int = 60
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # 统计看板缓存（秒，默认 5 分钟，统计结果不要求实时精确）
    DASHBOARD_CACHE_TTL: int = 300

    # 安全
    SECRET_KEY: str = "dev-only-change-me-in-production-32b"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_BCRYPT_ROUNDS: int = 12

    # 登录限流（固定窗口）：按 IP 限制登录尝试，防爆破
    LOGIN_RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 5  # 窗口内最大尝试次数
    LOGIN_RATE_LIMIT_WINDOW: int = 300  # 窗口时长（秒），默认 5 分钟

    # 种子数据
    SEED_ADMIN_USERNAME: str = "admin"
    SEED_ADMIN_PASSWORD: str = "admin123"
    SEED_ADMIN_EMAIL: str = "admin@vulnscope.local"

    def database_url(self) -> str:
        """返回完整数据库连接 URL。

        Returns:
            DATABASE_URL 显式设置时优先返回，否则按 DB_BACKEND 拼接默认 URL。
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return DB_URLS.get(self.DB_BACKEND, DB_URLS["sqlite"])

    # 默认开发密钥特征：生产环境使用将导致 JWT 可被伪造，必须拦截。
    _DEFAULT_SECRET_KEY = "dev-only-change-me-in-production-32b"

    def validate_security(self) -> None:
        """生产环境安全配置校验：拒绝默认 SECRET_KEY。

        prod 环境下 SECRET_KEY 仍为内置开发密钥时抛错，强制运维注入随机密钥，
        避免 JWT 签名密钥泄露导致鉴权体系失守。dev/test 环境放行。
        """
        if self.APP_ENV != "prod":
            return
        if not self.SECRET_KEY or self.SECRET_KEY == self._DEFAULT_SECRET_KEY:
            raise RuntimeError(
                "生产环境(APP_ENV=prod)必须配置随机 SECRET_KEY，"
                "推荐执行 `openssl rand -hex 32` 生成并通过 VULNSCOPE_SECRET_KEY 注入"
            )
        if len(self.SECRET_KEY) < 32:
            raise RuntimeError("生产环境 SECRET_KEY 长度须不少于 32 字节")


@lru_cache
def get_settings() -> Settings:
    """获取 Settings 单例（lru_cache 保证进程内仅初始化一次）。"""
    return Settings()


settings = get_settings()
