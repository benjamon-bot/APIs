import oracledb
import requests
import os
from dotenv import load_dotenv
import bcrypt
from typing import Optional, Tuple
import datetime
import re

load_dotenv()

username = os.getenv("ORACLE_USER")
dsn = os.getenv("ORACLE_DSN")
password = os.getenv("ORACLE_PASSWORD")


def validar_username(u: str) -> bool:
   
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", u))

def validar_password(p: str) -> bool:

    if len(p) < 8 or len(p) > 128:
        return False
    return bool(re.search(r"[A-Za-z]", p) and re.search(r"\d", p))

def validar_opcion_menu(op: str, rango: Tuple[int, int]) -> bool:
    return op.isdigit() and rango[0] <= int(op) <= rango[1]

def hoy_dd_mm_yyyy() -> str:
    now = datetime.datetime.now()
    return f"{now.day}-{now.month}-{now.year}"


class Database:
    def __init__(self, username: str, password: str, dsn: str):
        self.username = username
        self.dsn = dsn
        self.password = password

    def get_connection(self):
        return oracledb.connect(user=self.username, password=self.password, dsn=self.dsn)
   
    def create_all_tables(self):
        tables = [
           
            """
            CREATE TABLE USERS(
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                username VARCHAR2(32) UNIQUE NOT NULL,
                password VARCHAR2(128) NOT NULL
            )
            """,
            """
            CREATE TABLE indicator_log(
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                indicator_name VARCHAR2(20) NOT NULL,
                indicator_value NUMBER NOT NULL,
                indicator_date DATE NOT NULL,
                query_date DATE NOT NULL,
                username VARCHAR2(50) NOT NULL,
                source VARCHAR2(100) NOT NULL
            )
            """
        ]

        for table in tables:
            try:
                self.query(table.strip())
            except Exception:
                pass

    def query(self, sql: str, parameters: Optional[dict] = None):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    ejecucion = cur.execute(sql, parameters or {})
                    if sql.strip().upper().startswith("SELECT"):
                        return list(ejecucion)
                conn.commit()
        except oracledb.DatabaseError as error:
            print("Error de base de datos:", error)
            return None

class Auth:
    @staticmethod
    def register(db: Database, username: str, password: str) -> bool:
        if not validar_username(username):
            print("Usuario inválido. Debe ser alfanumérico (._-) y de 3 a 32 caracteres.")
            return False
        if not validar_password(password):
            print("Contraseña inválida. Debe tener entre 8 y 128 caracteres con letras y números.")
            return False

        salt = bcrypt.gensalt(rounds=12)
        hash_password = bcrypt.hashpw(password.encode("UTF-8"), salt)
        hash_hex = hash_password.hex()

        try:
            db.query(
                sql= "INSERT INTO USERS(username,password) VALUES (:username, :password)",
                parameters={"username": username, "password": hash_hex}
            )
            print("Usuario registrado con éxito")
            return True
        except Exception as e:
            print("No se pudo registrar el usuario:", e)
            return False

    @staticmethod
    def login(db: Database, username: str, password: str) -> bool:
        if not validar_username(username) or not validar_password(password):
            print("Credenciales con formato inválido.")
            return False

        resultado = db.query(
            sql= "SELECT id, username, password FROM USERS WHERE username = :username",
            parameters={"username": username}
        )
        if not resultado:
            print("No hay coincidencias")
            return False
       
        # password almacenado como hex
        hashed_hex = resultado[0][2]
        try:
            hashed_password = bytes.fromhex(hashed_hex)
        except ValueError:
            print("Formato de hash inválido en base de datos.")
            return False

        if bcrypt.checkpw(password.encode("UTF-8"), hashed_password):
            print("Logeado correctamente")
            return True
        else:
            print("Contraseña incorrecta")
            return False


class Finance:
    def __init__(self, base_url: str = "https://mindicador.cl/api"):
        self.base_url = base_url

    def _fetch_indicator(self, indicator: str, fecha: Optional[str] = None) -> Optional[dict]:
        # fecha formato dd-mm-yyyy (API permite /indicador y /indicador/dd-mm-yyyy)
        if not fecha:
            fecha = hoy_dd_mm_yyyy()
        try:
            url = f"{self.base_url}/{indicator}/{fecha}"
            respuesta = requests.get(url, timeout=10)
            data = respuesta.json()
            serie = data.get("serie", [])
            if not serie:
                print("No hay datos para la fecha solicitada.")
                return None
            # Primer elemento: valor y fecha
            return {
                "value": float(serie[0]["valor"]),
                "indicator_date": datetime.datetime.strptime(serie[0]["fecha"][:10], "%Y-%m-%d").date(),
                "source": self.base_url
            }
        except Exception:
            print("Hubo un error con la solicitud")
            return None

    def consultar_y_opcionalmente_guardar(self, db: Database, username: str, indicador: str, fecha: Optional[str] = None):
        data = self._fetch_indicator(indicador, fecha)
        if not data:
            return

        print(f"{indicador.upper()} al {data['indicator_date']}: {data['value']}")
        guardar = input("¿Desea registrar esta consulta en la base de datos? (s/n): ").strip().lower()
        if guardar == "s":
            self._registrar_consulta(
                db=db,
                username=username,
                indicator_name=indicador,
                indicator_value=data["value"],
                indicator_date=data["indicator_date"],
                source=data["source"]
            )
            print("Consulta registrada.")
        else:
            print("Consulta no registrada.")

    def _registrar_consulta(self, db: Database, username: str, indicator_name: str, indicator_value: float, indicator_date: datetime.date, source: str):
        query_date = datetime.date.today()
        db.query(
            sql="""
                INSERT INTO indicator_log(
                    indicator_name, indicator_value, indicator_date, query_date, username, source
                ) VALUES (:name, :value, :ind_date, :qry_date, :username, :source)
            """,
            parameters={
                "name": indicator_name,
                "value": indicator_value,
                "ind_date": indicator_date,
                "qry_date": query_date,
                "username": username,
                "source": source
            }
        )

    def get_usd(self, db: Database, username: str, fecha: Optional[str] = None):
        self.consultar_y_opcionalmente_guardar(db, username, "dolar", fecha)

    def get_eur(self, db: Database, username: str, fecha: Optional[str] = None):
        self.consultar_y_opcionalmente_guardar(db, username, "euro", fecha)

    def get_uf(self, db: Database, username: str, fecha: Optional[str] = None):
        self.consultar_y_opcionalmente_guardar(db, username, "uf", fecha)

    def get_ivp(self, db: Database, username: str, fecha: Optional[str] = None):
        self.consultar_y_opcionalmente_guardar(db, username, "ivp", fecha)

    def get_ipc(self, db: Database, username: str, fecha: Optional[str] = None):
        self.consultar_y_opcionalmente_guardar(db, username, "ipc", fecha)

    def get_utm(self, db: Database, username: str, fecha: Optional[str] = None):
        self.consultar_y_opcionalmente_guardar(db, username, "utm", fecha)

# -----------------------------
# Menús
# -----------------------------
def menu_principal():
    print(
        """
            ====================================
            |         Menu Principal           |
            |----------------------------------|
            | 1. Iniciar sesión                |
            | 2. Registrarse                   |
            | 3. Salir                         |
            ====================================
        """
    )

def menu_indicadores():
    print(
        """
            ====================================
            |           Indicadores            |
            |----------------------------------|
            | 1. UF                            |
            | 2. Dólar                         |
            | 3. Euro                          |
            | 4. IVP                           |
            | 5. IPC                           |
            | 6. UTM                           |
            | 7. Volver                        |
            ====================================
        """
    )

if __name__ == "__main__":
    db = Database(username=username, password=password, dsn=dsn)
    fin = Finance()
    db.create_all_tables()

    while True:
        menu_principal()
        opcion = input("Seleccione una opción: ").strip()
       
        if opcion == "1":
            usuario = input("Usuario: ").strip()
            contrasenia = input("Contraseña: ").strip()

            if Auth.login(db, usuario, contrasenia):
                print("Bienvenido", usuario)
                while True:
                    menu_indicadores()
                    op = input("Seleccione indicador: ").strip()

                    if op == "1":
                        fin.get_uf(db, usuario)
                    elif op == "2":
                        fin.get_usd(db, usuario)
                    elif op == "3":
                        fin.get_eur(db, usuario)
                    elif op == "4":
                        fin.get_ivp(db, usuario)
                    elif op == "5":
                        fin.get_ipc(db, usuario)
                    elif op == "6":
                        fin.get_utm(db, usuario)
                    elif op == "7":
                        break
                    else:
                        print("Opción no válida")
            else:
                print("Usuario o contraseña incorrectos")

        elif opcion == "2":
            nuevo_usuario = input("Nuevo usuario: ").strip()
            nueva_contrasenia = input("Nueva contraseña: ").strip()
            Auth.register(db, nuevo_usuario, nueva_contrasenia)

        elif opcion == "3":
            print("Saliendo del sistema...")
            break
        else:
            print("Opción inválida")