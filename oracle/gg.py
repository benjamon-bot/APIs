import bcrypt
import requests
import oracledb
import os
import re
from dotenv import load_dotenv
from typing import Optional, Tuple
import datetime

load_dotenv()


# ------------------------------
# Database access layer (Oracle)
# ------------------------------
class Database:
    def __init__(self, username: str, dsn: str, password: str):
        self.username = username
        self.dsn = dsn
        self.password = password

    def get_connection(self):
        return oracledb.connect(user=self.username, password=self.password, dsn=self.dsn)

    def create_all_tables(self):
        tables = [
            (
                "CREATE TABLE USERS ("
                "  id NUMBER PRIMARY KEY,"
                "  username VARCHAR2(32) UNIQUE NOT NULL,"
                "  password VARCHAR2(128) NOT NULL"
                ")"
            ),
            (
                "CREATE TABLE INDICATOR_LOGS ("
                "  id NUMBER PRIMARY KEY,"
                "  indicator_name VARCHAR2(32) NOT NULL,"
                "  indicator_value NUMBER(18,4) NOT NULL,"
                "  indicator_date DATE NOT NULL,"
                "  query_date DATE NOT NULL,"
                "  username VARCHAR2(32) NOT NULL,"
                "  provider VARCHAR2(128) NOT NULL"
                ")"
            )
        ]
        for ddl in tables:
            try:
                self.query(ddl)
            except Exception as e:
                # If table exists, Oracle will raise an error; we can ignore for idempotency
                pass

    def query(self, sql: str, parameters: Optional[dict] = None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                ejecucion = cur.execute(sql, parameters or {})
                if sql.strip().upper().startswith("SELECT"):
                    return ejecucion.fetchall()
            conn.commit()

    def next_id(self, table: str) -> int:
        rows = self.query(f"SELECT NVL(MAX(id), 0) FROM {table}")
        current = rows[0][0] if rows else 0
        return int(current) + 1


# ------------------------------
# Input validation utilities
# ------------------------------
class Validator:
    USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")

    @staticmethod
    def validate_username(username: str) -> bool:
        return bool(Validator.USERNAME_RE.match(username))

    @staticmethod
    def validate_password(password: str) -> bool:
        # At least 8 chars, 1 letter, 1 number
        return (
            isinstance(password, str)
            and len(password) >= 8
            and re.search(r"[A-Za-z]", password) is not None
            and re.search(r"\d", password) is not None
        )

    @staticmethod
    def validate_indicator(indicator: str) -> bool:
        allowed = {"uf", "ivp", "ipc", "utm", "dolar", "euro"}
        return indicator in allowed

    @staticmethod
    def parse_date_dd_mm_yyyy(fecha: Optional[str]) -> Tuple[datetime.datetime, str]:
        """
        Returns (date_obj, formatted_dd-mm-yyyy). If fecha is None, uses today's date in Chile format.
        """
        if not fecha:
            now = datetime.datetime.now()
            formatted = f"{now.day:02d}-{now.month:02d}-{now.year}"
            return now, formatted

        if not re.match(r"^\d{2}-\d{2}-\d{4}$", fecha):
            raise ValueError("La fecha debe estar en formato DD-MM-YYYY.")

        dd, mm, yyyy = map(int, fecha.split("-"))
        return datetime.datetime(yyyy, mm, dd), fecha


# ------------------------------
# Authentication service
# ------------------------------
class Auth:
    @staticmethod
    def register(db: Database, username: str, password: str) -> bool:
        if not Validator.validate_username(username):
            print("Usuario inválido. Use 3-32 caracteres alfanuméricos o _.")
            return False
        if not Validator.validate_password(password):
            print("Contraseña inválida. Mínimo 8 caracteres, al menos una letra y un número.")
            return False

        # Check if username exists
        existing = db.query(
            "SELECT id FROM USERS WHERE username = :username",
            {"username": username}
        )
        if existing:
            print("El usuario ya existe.")
            return False

        salt = bcrypt.gensalt(rounds=12)
        hash_password = bcrypt.hashpw(password.encode("utf-8"), salt).hex()
        new_id = db.next_id("USERS")
        db.query(
            "INSERT INTO USERS (id, username, password) VALUES (:id, :username, :password)",
            {"id": new_id, "username": username, "password": hash_password}
        )
        print("Usuario registrado con éxito.")
        return True

    @staticmethod
    def login(db: Database, username: str, password: str) -> bool:
        if not Validator.validate_username(username):
            print("Usuario inválido.")
            return False

        rows = db.query(
            "SELECT id, username, password FROM USERS WHERE username = :username",
            {"username": username}
        )
        if not rows:
            print("No hay coincidencias.")
            return False

        stored_hex = rows[0][2]
        hashed_password = bytes.fromhex(stored_hex)

        if bcrypt.checkpw(password.encode("utf-8"), hashed_password):
            print("Logeado correctamente.")
            return True
        else:
            print("Contraseña incorrecta.")
            return False


# ------------------------------
# Finance service (mindicador.cl)
# ------------------------------
class Finance:
    def __init__(self, base_url: str = "https://mindicador.cl/api"):
        self.base_url = base_url

    def get_indicator(self, indicator: str, fecha: Optional[str] = None) -> Tuple[float, datetime.datetime]:
        if not Validator.validate_indicator(indicator):
            raise ValueError("Indicador inválido. Use uno de: uf, ivp, ipc, utm, dolar, euro.")

        try:
            date_obj, fecha_fmt = Validator.parse_date_dd_mm_yyyy(fecha)
            url = f"{self.base_url}/{indicator}/{fecha_fmt}"
            respuesta = requests.get(url, timeout=10).json()

            serie = respuesta.get("serie", [])
            if not serie:
                raise ValueError("Sin datos para la fecha solicitada.")

            valor = float(serie[0]["valor"])
            # API 'fecha' may include ISO string; we trust our requested date for logging
            return valor, date_obj
        except Exception as e:
            print(f"Hubo un error con la solicitud: {e}")
            raise

    def get_usd(self, fecha: Optional[str] = None) -> Tuple[float, datetime.datetime]:
        return self.get_indicator("dolar", fecha)

    def get_eur(self, fecha: Optional[str] = None) -> Tuple[float, datetime.datetime]:
        return self.get_indicator("euro", fecha)

    def get_uf(self, fecha: Optional[str] = None) -> Tuple[float, datetime.datetime]:
        return self.get_indicator("uf", fecha)

    def get_ivp(self, fecha: Optional[str] = None) -> Tuple[float, datetime.datetime]:
        return self.get_indicator("ivp", fecha)

    def get_ipc(self, fecha: Optional[str] = None) -> Tuple[float, datetime.datetime]:
        return self.get_indicator("ipc", fecha)

    def get_utm(self, fecha: Optional[str] = None) -> Tuple[float, datetime.datetime]:
        return self.get_indicator("utm", fecha)


# ------------------------------
# Application session and logging
# ------------------------------
class AppSession:
    def __init__(self, db: Database, finance: Finance, provider: str = "https://mindicador.cl/api"):
        self.db = db
        self.finance = finance
        self.provider = provider
        self.current_user: Optional[str] = None

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def login(self):
        username = input("Usuario: ").strip()
        password = input("Contraseña: ").strip()
        if Auth.login(self.db, username, password):
            self.current_user = username

    def register(self):
        username = input("Nuevo usuario: ").strip()
        password = input("Nueva contraseña: ").strip()
        Auth.register(self.db, username, password)

    def query_indicator(self):
        if not self.is_logged_in():
            print("Debe iniciar sesión para consultar indicadores.")
            return

        indicador = input("Indicador (uf, ivp, ipc, utm, dolar, euro): ").strip().lower()
        fecha = input("Fecha (DD-MM-YYYY) o vacío para hoy: ").strip()
        fecha = fecha if fecha else None

        if not Validator.validate_indicator(indicador):
            print("Indicador inválido.")
            return

        try:
            valor, fecha_valor = self.finance.get_indicator(indicador, fecha)
            print(f"{indicador.upper()} al {fecha_valor.strftime('%d-%m-%Y')}: {valor}")

            # Log to DB
            new_id = self.db.next_id("INDICATOR_LOGS")
            now = datetime.datetime.now()
            self.db.query(
                "INSERT INTO INDICATOR_LOGS (id, indicator_name, indicator_value, indicator_date, query_date, username, provider) "
                "VALUES (:id, :indicator_name, :indicator_value, :indicator_date, :query_date, :username, :provider)",
                {
                    "id": new_id,
                    "indicator_name": indicador,
                    "indicator_value": valor,
                    "indicator_date": fecha_valor,
                    "query_date": now,
                    "username": self.current_user,
                    "provider": self.provider
                }
            )
            print("Consulta registrada en la base de datos.")
        except Exception:
            # Error already printed in Finance.get_indicator
            pass

    def view_my_logs(self):
        if not self.is_logged_in():
            print("Debe iniciar sesión para ver sus registros.")
            return

        rows = self.db.query(
            "SELECT indicator_name, indicator_value, indicator_date, query_date, provider "
            "FROM INDICATOR_LOGS WHERE username = :username ORDER BY query_date DESC",
            {"username": self.current_user}
        )
        if not rows:
            print("No hay registros.")
            return

        for name, value, indicator_date, query_date, provider in rows:
            ind_date_str = indicator_date.strftime("%d-%m-%Y") if isinstance(indicator_date, datetime.datetime) else str(indicator_date)
            q_date_str = query_date.strftime("%d-%m-%Y %H:%M:%S") if isinstance(query_date, datetime.datetime) else str(query_date)
            print(f"{name.upper()} | Valor: {value} | Fecha valor: {ind_date_str} | Consultado: {q_date_str} | Fuente: {provider}")


# ------------------------------
# CLI Menu
# ------------------------------
def main():
    db = Database(
        username=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN")
    )
    db.create_all_tables()

    finance = Finance()
    app = AppSession(db, finance)

    while True:
        print("\n=== Menú ===")
        print("1. Registrarse")
        print("2. Iniciar sesión")
        print("3. Consultar indicador")
        print("4. Ver mis registros")
        print("5. Salir")

        choice = input("Seleccione una opción: ").strip()
        if choice == "1":
            app.register()
        elif choice == "2":
            app.login()
        elif choice == "3":
            app.query_indicator()
        elif choice == "4":
            app.view_my_logs()
        elif choice == "5":
            print("Adiós.")
            break
        else:
            print("Opción inválida.")


if __name__ == "__main__":
    main()
