from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_", env_file=".env", extra="ignore")

    use_real_models: bool = True
    face_match_threshold: float = 0.50
    tamper_flag_threshold: float = 0.55
    ela_quality: int = 90


settings = Settings()
