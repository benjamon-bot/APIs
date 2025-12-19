"""
saludar al ususario al ingrsar su nombre
"""
import flet as ft

class App:
    def __init__(self,page: ft.Page):
        self.page =page
        self.page.title="hola mundo"
        self.input_nombre= ft.TextField(
                label="nombre",
                hint_text="ingresa tu nombre"
            )
        self.button_saludar= ft.Button(
                text="saludar",
                on_click=self.on_saludar
            )
        self.text_saludar=ft.Text(
                value=""
            )
        self.build()
        
    def build(self):
        self.page.add(
            self.input_nombre,
            self.button_saludar,
            self.text_saludar
        )
    def on_saludar(self,e):
        nombre=(self.input_nombre.value or "").strip()
        if not nombre:
            self.text_saludar.value="ingresa un nombre."
        else:
            self.text_saludar.value=f"hola{nombre}"
        self.page.update()

if __name__ == "__main__":
    ft.app(target=App)