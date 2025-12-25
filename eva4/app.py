import os
import datetime
import flet as ft
from dotenv import load_dotenv
from ecotech import Auth, Database, Finance

load_dotenv()

class Aplicacion:
    def __init__(self, pagina: ft.Page):
        self.pagina = pagina
        self.pagina.title = "Solución Ecotech"
        self.pagina.window_width = 500
        self.pagina.window_height = 800
        self.pagina.theme_mode = ft.ThemeMode.LIGHT

        # Inicializar base de datos y API
        self.db = Database(
            usuario=os.getenv("ORACLE_USER"),
            contrasena=os.getenv("ORACLE_PASSWORD"),
            dsn=os.getenv("ORACLE_DSN")
        )
        self.db.crear_tablas()
        self.finanzas = Finance()
        self.usuario_logeado = None

        # DatePicker para elegir fechas
        self.date_picker = ft.DatePicker(
            first_date=datetime.datetime(2000, 1, 1),
            last_date=datetime.datetime.now(),
            on_change=self._on_fecha_seleccionada
        )
        self.pagina.overlay.append(self.date_picker)

        # Buffers
        self._ultimo_resultado = None
        self._ultimo_indicador = None

        # Inicia en registro
        self.pantalla_registro()

    # -------------------------
    # Pantalla de registro
    # -------------------------
    def pantalla_registro(self):
        self.pagina.controls.clear()
        self.input_usuario = ft.TextField(label="Usuario")
        self.input_contrasena = ft.TextField(label="Contraseña", password=True, can_reveal_password=True)
        self.boton_registrar = ft.Button(text="Registrar", on_click=self.registrar)
        self.texto_estado = ft.Text(value="")
        self.boton_login = ft.Button(text="Ya tengo cuenta", on_click=lambda e: self.pantalla_login())
        self.pagina.add(self.input_usuario, self.input_contrasena, self.boton_registrar, self.texto_estado, self.boton_login)
        self.pagina.update()

    def registrar(self, e):
        usuario = (self.input_usuario.value or "").strip()
        contrasena = (self.input_contrasena.value or "").strip()
        estado = Auth.registrar(self.db, usuario, contrasena)
        self.texto_estado.value = estado["message"]
        self.texto_estado.color = ft.colors.GREEN_600 if estado["success"] else ft.colors.RED_400
        self.pagina.update()
        if estado["success"]:
            self.pantalla_login()

    # -------------------------
    # Pantalla de login
    # -------------------------
    def pantalla_login(self):
        self.pagina.controls.clear()
        self.input_usuario = ft.TextField(label="Usuario")
        self.input_contrasena = ft.TextField(label="Contraseña", password=True, can_reveal_password=True)
        self.boton_login = ft.Button(text="Iniciar sesión", on_click=self.login)
        self.texto_estado = ft.Text(value="")
        self.pagina.add(self.input_usuario, self.input_contrasena, self.boton_login, self.texto_estado)
        self.pagina.update()

    def login(self, e):
        usuario = (self.input_usuario.value or "").strip()
        contrasena = (self.input_contrasena.value or "").strip()
        estado = Auth.login(self.db, usuario, contrasena)
        self.texto_estado.value = estado["message"]
        self.texto_estado.color = ft.colors.GREEN_600 if estado["success"] else ft.colors.RED_400
        self.pagina.update()
        if estado["success"]:
            self.usuario_logeado = usuario
            self.pantalla_menu()

    # -------------------------
    # Pantalla principal
    # -------------------------
    def pantalla_menu(self):
        self.pagina.controls.clear()
        self.pagina.add(ft.Text(f"Bienvenido {self.usuario_logeado}", size=20))
        self.pagina.add(ft.Button(text="Consultar indicador", on_click=lambda e: self.pantalla_indicador()))
        self.pagina.add(ft.Button(text="Historial", on_click=lambda e: self.pantalla_historial()))
        self.pagina.add(ft.Button(text="Cerrar sesión", on_click=lambda e: self.pantalla_login()))
        self.pagina.update()

    # -------------------------
    # Pantalla de consulta de indicador
    # -------------------------
    def pantalla_indicador(self):
        self.pagina.controls.clear()
        self.dropdown_indicador = ft.Dropdown(
            label="Indicador",
            options=[
                ft.dropdown.Option("uf"),
                ft.dropdown.Option("dolar"),
                ft.dropdown.Option("euro"),
                ft.dropdown.Option("utm"),
                ft.dropdown.Option("ipc"),
                ft.dropdown.Option("ivp"),
            ],
            width=300
        )
        self.input_fecha = ft.TextField(label="Fecha", read_only=True, width=200)
        self.boton_fecha = ft.Button(text="Elegir fecha", on_click=lambda e: self.date_picker.pick_date())
        self.boton_consultar = ft.Button(text="Consultar", on_click=self.consultar_indicador)
        self.boton_guardar = ft.Button(text="Guardar consulta", on_click=self.guardar_indicador, disabled=True)
        self.texto_estado_indicador = ft.Text(value="", color=ft.colors.RED_400)
        self.texto_resultado = ft.Text(value="", selectable=True)
        self.pagina.add(self.dropdown_indicador, ft.Row([self.input_fecha, self.boton_fecha]), ft.Row([self.boton_consultar, self.boton_guardar]), self.texto_estado_indicador, self.texto_resultado, ft.Button(text="Volver", on_click=lambda e: self.pantalla_menu()))
        self.pagina.update()

    def _on_fecha_seleccionada(self, e):
        if self.date_picker.value:
            self.input_fecha.value = self.date_picker.value.strftime("%d-%m-%Y")
            self.pagina.update()

    def consultar_indicador(self, e):
        indicador = (self.dropdown_indicador.value or "").strip()
        fecha = (self.input_fecha.value or "").strip()
        datos = self.finanzas.obtener_indicador(indicador, fecha)
        if not datos.get("success"):
            self.texto_estado_indicador.value = datos.get("message", "Error")
            self.texto_estado_indicador.color = ft.colors.RED_400
            self.texto_resultado.value = ""
            self.boton_guardar.disabled = True
        else:
            self.texto_estado_indicador.value = "Consulta realizada"
            self.texto_estado_indicador.color = ft.colors.GREEN_600
            self.texto_resultado.value = f"{indicador.upper()} {fecha}: {datos['valor']} (Fuente: {datos['fuente']})"
            self._ultimo_resultado = datos
            self._ultimo_indicador = indicador
            self.boton_guardar.disabled = False
        self.pagina.update()

    def guardar_indicador(self, e):
        if self._ultimo_resultado:
            self.finanzas.guardar_consulta(self.db, self.usuario_logeado, self._ultimo_indicador, self._ultimo_resultado)
            self.texto_estado_indicador.value = "Consulta guardada"
            self.texto_estado_indicador.color = ft.colors.GREEN_600
            self.pagina.update()

    # -------------------------
    # Pantalla de historial
    # -------------------------
    def pantalla_historial(self):
        self.pagina.controls.clear()
        self.tabla = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Indicador")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Valor")),
                ft.DataColumn(ft.Text("Consulta")),
                ft.DataColumn(ft.Text("Fuente")),
            ],
            rows=[]
        )
        self.recargar_historial()
        self.pagina.add(ft.Text("Historial de consultas", size=20, weight=ft.FontWeight.BOLD), self.tabla, ft.Button(text="Volver", on_click=lambda e: self.pantalla_menu()))
        self.pagina.update()

    def recargar_historial(self):
        filas = self.db.ejecutar("SELECT indicador, fecha_indicador, valor, fecha_consulta, fuente FROM historial_consultas WHERE usuario=:usr", {"usr": self.usuario_logeado}) or []
        self.tabla.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(f[0]))),
                ft.DataCell(ft.Text(str(f[1]))),
                ft.DataCell(ft.Text(str(f[2]))),
                ft.DataCell(ft.Text(str(f[3]))),
                ft.DataCell(ft.Text(str(f[4]))),
            ]) for f in filas
        ]

def main(pagina: ft.Page):
    Aplicacion(pagina)

if __name__ == "__main__":
    ft.app(target=main)
