import bcrypt

# Hashear una contraseña
password = input('Ingrese la contraseña: ')
hashed_password = bcrypt.hashpw(password.encode(
    'utf-8'), bcrypt.gensalt()).decode('utf-8')

# Este es el valor que debes guardar en la base de datos
print("hash: " + hashed_password)
