from fastapi import APIRouter

version_router = APIRouter(tags=["version"])

SERVICE_VERSION = "0.1.0"
API_VERSION = "v1"


@version_router.get("/version")
def get_version() -> dict:
    return {"api_version": API_VERSION, "service_version": SERVICE_VERSION}
