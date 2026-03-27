import _load_env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import v1

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

app.include_router(v1.router)
