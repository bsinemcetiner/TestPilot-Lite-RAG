from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "TestPilot Lite RAG Backend"
    database_url: str = "sqlite:///./backend.db"

    class Config:
        extra = "ignore"


settings = Settings()
