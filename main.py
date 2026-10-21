from contextlib import asynccontextmanager

from fastapi import FastAPI

import database
from routers import auth, grupos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lo que va antes del 'yield' se ejecuta al arrancar; lo de después, al apagar."""
    await database.crear_pool()
    yield
    await database.cerrar_pool()


app = FastAPI(title="Compartir gastos", lifespan=lifespan)


app.include_router(auth.router)
app.include_router(grupos.router)


@app.get("/")
def raiz():
    return {"mensaje": "API de Compartir gastos funcionando"}