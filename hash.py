import bcrypt 

#paso 1. pedir contraseña
incoming_password = input("ingrese su contraseña: ").encode("UTF-8")
#paso 2. generar un salt
salt = bcrypt.gensalt(rounds=12)
#paso 3.hashear la contraseña con el salt
hashed_password=bcrypt.hashpw(incoming_password, salt)
print(hashed_password)

confirm_password= input("ingrese nuevamente la contraseña: ").encode("UTF-8")

if bcrypt.checkpw(confirm_password, hashed_password):
    print("contraseña correcta")
else:
    print("contraseña incorrecta")