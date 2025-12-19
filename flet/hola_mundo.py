#primer paso:importar flet
import flet as ft
#2.paso:establecer la clase de mi aplicacion
class App:
    def __init__(self,page: ft.Page):
        self.page =page
        self.page.title="hola mundo"
        #aplicar interfaz
        self.build()
    def build(self):
        self.page.add(
            ft.Text("hola mundo")
        )

#3.paso:ejecutar aplicacion
if __name__ == "__main__":
    ft.app(target=App)