from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VAR_",
        env_file=".env",
        extra="ignore",
    )

    api_key: str = ""
    api_base_url: str = ""

    # Path to the catalog runtime directory. Must contain a `registry/` subdir with
    # the 7 required JSON files. Defaults to the repo-local `catalog-runtime/`.
    catalog_runtime_dir: str = str(
        (Path(__file__).resolve().parents[1] / "catalog-runtime").resolve()
    )
    command_timeout_seconds: int = 20
    max_output_chars: int = 12000

    # MCP identity — override per-deployment via VAR_SERVER_NAME.
    server_name: str = "tin-canMCP"


settings = ApiSettings()
