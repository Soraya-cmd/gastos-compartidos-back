
from fastapi import FastAPI


app = FastAPI(title="Compartir gastos")


@app.get("/")
def raiz():
    return {"mensaje": "API de Compartir gastos funcionando"}