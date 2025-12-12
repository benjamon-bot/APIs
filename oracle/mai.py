import oracledb
import os
import requests
import bcrypt
import requests
from dotenv import load_dotenv
from typing import Optional
import datetime
load_dotenv()

class database:
    def __init__(self,username,password,dsn):
        self.username=username
        self.password=password
        self.dsn=dsn
    
    def get_connection(self):
        return oracledb.connect(user=self.username, password=self.password, dsn=self.dsn)
    def create_all_tables(self):
         tables = [
             (
                "CREATE TABLE USERS ("
                "id INTEGER PRIMARY KEY,"
                "username VARCHAR2(32) UNIQUE,"
                "password VARCHAR2(128)"
                ")"
             )
         ]

    def query(self, sql:str, parameters: Optional[dict]):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    resultado=cur.execute(sql,parameters)
                    return resultado
                conn.commit()
        except oracledb.DatabaseError as error:
            print(error)

 
class auth:
    @staticmethod
    def login(db: database,username: str,password: str):
        pass
    @staticmethod
    def register(db: database,username: str,password: str):
        password=password.encode("UTF-8")
        salt=bcrypt.gensalt(12)
        hash_password=bcrypt.hashpw(password,salt)

        usuario={
            "id":
            "username"
            "password"
        }


class Finance:
    def __init__(self,base_url:str = "https://mindicador.cl/api" ):
        self.base_url=base_url
    def get_inicator(self,inidicator:str , fecha:str = None)-> float:
        try:
            if not fecha:
                dd=datetime.datetime.now().day
                mm=datetime.datetime.now().month
                yyyy=datetime.datetime.now().year
                fecha=f"{dd}-{mm}-{yyyy}"
            url=f"{self.base_url}/{inidicator}/{fecha}"
            respuesta=requests.get(url).json()
            print(respuesta["serie"][0]["valor"])
        except:
            print("hubo un error con la solicitud")
    def get_usd(self,fecha:str=None):
        valor=self.get_inicator("dolar",fecha)
        print(f"el valor del dolar en CLP es: {valor}")
    def get_eur(self,fecha:str=None):
        self.get_inicator("euro",fecha)
    def get_uf(self,fecha:str=None):
        self.get_inicator("uf",fecha)
    def get_ivp(self,fecha:str=None):
        self.get_inicator("ivp",fecha)
    def get_ipc(self,fecha:str=None):
        self.get_inicator("ipc",fecha)
    def get_utm(self,fecha:str=None):
        self.get_inicator("utm",fecha)


if __name__ == "__main__":
    indicadores=Finance()
    indicadores.get_usd("28-11-2025")

