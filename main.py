from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
from config import CORS_ORIGINS
from routers import auth, grupos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lo que va antes del 'yield' se ejecuta al arrancar; lo de después, al apagar."""
    await database.crear_pool()
    yield
    await database.cerrar_pool()


app = FastAPI(title="Compartir gastos", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(grupos.router)


@app.get("/")
def raiz():
    return {"mensaje": "API de Compartir gastos funcionando"}