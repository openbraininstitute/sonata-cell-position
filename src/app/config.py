"""Configuration."""

import re

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
    )

    APP_NAME: str = "cell-service"
    APP_VERSION: str | None = None
    COMMIT_SHA: str = "UNDEFINED"
    APP_DEBUG: bool = False
    UVICORN_PORT: int = 8010
    ROOT_PATH: str = ""

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    LOG_SERIALIZE: bool = True
    LOG_BACKTRACE: bool = False
    LOG_DIAGNOSE: bool = False
    LOG_ENQUEUE: bool = False
    LOG_CATCH: bool = True
    LOG_STANDARD_LOGGER: dict[str, str] = {"root": "INFO"}

    # maximum sampling ratio considered for caching
    CACHED_SAMPLING_RATIO: float = 0.01

    KEYCLOAK_URL: str = "https://example.openbluebrain.com/auth/realms/SBO"
    KEYCLOAK_AUTH_TIMEOUT: float = 10  # in seconds

    LOKY_EXECUTOR_ENABLED: bool = True
    LOKY_EXECUTOR_MAX_WORKERS: int = 4  # maximum number of workers
    # seconds after which idle workers automatically shutdown. any value greater than 2147483
    # (around 24.86 days) would cause OverflowError: timeout is too large
    LOKY_EXECUTOR_TIMEOUT: float = 2**31 // 1000
    LOKY_START_METHOD: str = "loky"

    # circuit cache saved to disk (ideally RAM disk)
    CIRCUIT_CACHE_INFO: bool = False  # hits and misses
    CIRCUIT_CACHE_MAX_SIZE_MB: float = 400
    CIRCUIT_CACHE_CHECK_TIMEOUT: float = 600  # in seconds
    CIRCUIT_CACHE_CHECK_INTERVAL: float = 1  # in seconds

    # The tag should match NEXT_PUBLIC_BRAIN_REGION_ONTOLOGY_RESOURCE_TAG
    # in https://github.com/openbraininstitute/core-web-app/blob/main/.env
    # and the corresponding file should be bundled in app/data.
    # It will be possible to remove this parameter if/when it can be obtained in other ways, e.g:
    # - from the circuit resource in entitycore, or
    # - from the frontend when the circuit endpoint is called
    BRAIN_REGION_ONTOLOGY_BUNDLED_FILE: str = "brainregion_v2.1.0.json"
    BRAIN_REGION_ONTOLOGY_ID_PATTERN: re.Pattern = re.compile(r"https?://.*/Structure/(\d+)$")
    # The corresponding file should be bundled in app/data.
    HIERARCHY_BUNDLED_FILE: str = "hierarchy.json"


settings = Settings()
