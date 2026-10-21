from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends

import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lo que va antes del 'yield' se ejecuta al arrancar; lo de después, al apagar."""
    await database.crear_pool()
    yield
    await database.cerrar_pool()


app = FastAPI(title="Compartir gastos", lifespan=lifespan)


@app.get("/")
def raiz():
    return {"mensaje": "API de Compartir gastos funcionando"}



@app.get("/salud-bd")
async def salud_bd(conexion=Depends(database.get_conexion)):
    async with conexion.cursor() as cursor:
        await cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
        fila = await cursor.fetchone()
    return {"bd": "conectada", "usuarios": fila["total"]}