import oracledb
conn = oracledb.connect(user="tu_usuario", password="tu_contraseña", dsn="localhost:1521/XEPDB1")
print("Conexión OK")
conn.close()