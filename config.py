import os
from dotenv import load_dotenv

load_dotenv()


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")


for nombre, valor in [("DB_USER", DB_USER), ("DB_PASSWORD", DB_PASSWORD),
                      ("DB_NAME", DB_NAME), ("SECRET_KEY", SECRET_KEY)]:
    if not valor:
        raise RuntimeError(f"Falta la variable {nombre} en el archivo .env")





    


CORS_ORIGINS = [
    origen.strip()
    for origen in os.getenv("CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
    if origen.strip()
]