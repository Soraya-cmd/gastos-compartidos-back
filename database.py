import aiomysql
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


pool = None


async def crear_pool():
    """Se ejecuta una vez, al arrancar la aplicación."""
    global pool
    pool = await aiomysql.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset="utf8mb4",
        autocommit=True,                  # guarda los cambios automáticamente
        cursorclass=aiomysql.DictCursor,  # devuelve cada fila como diccionario
    )


async def cerrar_pool():
    """Se ejecuta una vez, al apagar la aplicación."""
    pool.close()
    await pool.wait_closed()


async def get_conexion():
    """Presta una conexión a cada ruta que la pida y la devuelve al terminar."""
    async with pool.acquire() as conexion:
        yield conexion