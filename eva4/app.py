"""
saludar al ususario al ingrsar su nombre
"""
import flet as ft
from ecotech import Auth , Database , Finance
class App:
    def __init__(self,page: ft.Page):
        self.page=page
        self.page.title="ecotech solution"
        self.finance=Finance()
        self.usd_button=ft.Button(
            text="consultar USD actual",
            on_click=self.get_usd
        )
        self.build(
            
        )
        
    def build(self):
        self.page.add(
            self.usd_button
        )

    def get_usd(self,e):
        self.finance.get_usd()

if __name__ == "__main__":
    ft.app(target=App)