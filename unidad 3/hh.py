import oracledb
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

username=os.getenv("ORACLE_USER")
dsn=os.getenv("ORACLE_DSN")
password=os.getenv("ORACLE_PASSWORD")

def get_connection():
    return oracledb.connect(
        user=username,
        password=password,
        dsn=dsn
    )

def create_schema(query):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                print(f"Tabla creada \n {query}")
            conn.commit()
    except oracledb.DatabaseError as e:
        err = e
        print(f"No se pudo crear la tabla: {err} \n {query}")

def create_table_users():
    query=(
        "CREATE TABLE"
        ""
        ""

    )

incoming_password=input("ingresa una contraseña: ").encode("UTF-8")
salt=bcrypt.gensalt(rounds=12)
hashed_password=bcrypt.hashpw(incoming_password,salt)

print(f"contraseña obtenida: {incoming_password}")
print(f"contraseña hasheada: {hashed_password}")

