from fastapi import APIRouter
from routes.workflow import router as workflow_router

api_router = APIRouter()
api_router.include_router(workflow_router, prefix="", tags=["Workflows"])
