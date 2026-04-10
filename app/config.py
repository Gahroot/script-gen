from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    host: str = "0.0.0.0"
    port: int = 8100
    gemini_model: str = "gemini-2.5-flash"
    max_regeneration_loops: int = 3

    # Email delivery (optional) — set RESEND_API_KEY to enable
    resend_api_key: str = ""
    resend_from_email: str = "Script Gen <onboarding@resend.dev>"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
