from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "Asset Guardian"
    
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "asset_guardian"
    POSTGRES_PORT: str = "5432"
    
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    OPENAI_API_KEY: str = "your-openai-api-key"
    ANTHROPIC_API_KEY: str = "your-anthropic-api-key"
    SECRET_KEY: str = "insecure-default-key-for-dev"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
