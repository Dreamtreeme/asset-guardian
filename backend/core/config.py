from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Asset Guardian"
    
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./test.db"
    
    OPENAI_API_KEY: str = "your-openai-api-key"
    ANTHROPIC_API_KEY: str = "your-anthropic-api-key"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
