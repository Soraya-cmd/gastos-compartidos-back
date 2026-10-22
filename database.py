import ssl

import aiomysql
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_SSL


pool = None


def crear_contexto_ssl():
    """Si DB_SSL es true, devuelve la configuración para conectar con SSL
    (conexión cifrada). Si no, devuelve None y se conecta como siempre."""
    if not DB_SSL:
        return None
    contexto = ssl.create_default_context()
  
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    return contexto


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
        autocommit=True,                  
        cursorclass=aiomysql.DictCursor,  
        ssl=crear_contexto_ssl(),         
    )


async def cerrar_pool():
    """Se ejecuta una vez, al apagar la aplicación."""
    pool.close()
    await pool.wait_closed()


async def get_conexion():
    """Presta una conexión a cada ruta que la pida y la devuelve al terminar."""
    async with pool.acquire() as conexion:
        yield conexion