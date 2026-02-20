import os

# Obtiene la ruta absoluta del directorio donde está este archivo
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 1. Seguridad
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-local-para-desarrollo'

    # 2. Base de Datos (La línea clave para ambos entornos)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 3. Configuración de Correo
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['neronl2es@gmail.com']
