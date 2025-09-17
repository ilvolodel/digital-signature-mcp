from pydantic_settings import BaseSettings  # type: ignore

class Settings(BaseSettings):
    CLIENT_ID: str
    CLIENT_SECRET: str
    SIGNATURE_API: str
    AUTHORIZATION_API: str
    TENANT: str
    
    # DigitalOcean Spaces configuration
    DO_SPACES_ACCESS_KEY: str
    DO_SPACES_SECRET_KEY: str
    DO_SPACES_REGION: str = "nyc3"
    DO_SPACES_BUCKET: str
    DO_SPACES_ENDPOINT: str = "https://nyc3.digitaloceanspaces.com"

settings = Settings()