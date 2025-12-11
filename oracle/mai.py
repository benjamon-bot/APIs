import oracledb
import os
from dotenv import load_dotenv

import bcrypt

import requests

load_dotenv()

class database:
    def __init__(self,username,password,dsn):
        self.username=username
        self.password=password
        self.dsn=dsn
    
    def get_connection(self):
        return oracledb.connect(user=self.username, password=self.password, dsn=self.dsn)
    def create_all_tables(self):
        pass
    def query(self, sql:str, parameters: Optional[dict]):
        pass

class auth:
    @staticmethod
    def login(db: database,username: str,password: str):
        pass
    @staticmethod
    def register(db: database,username: str,password: str):
        pass