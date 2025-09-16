from pydantic_settings import BaseSettings  # type: ignore

class Settings(BaseSettings):
    CLIENT_ID: str
    CLIENT_SECRET: str
    SIGNATURE_API: str
    AUTHORIZATION_API: str
    TENANT: str

settings = Settings()