import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Carga el .env solo si no estamos en producción (desarrollo local)
if os.environ.get('GAE_ENV') != 'standard':
    load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Configuraciones base para la aplicación Flask."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-por-defecto'

    # Lógica para la URI de la base de datos
    if os.environ.get('GAE_ENV') == 'standard':
        # Configuración para producción en Google Cloud SQL
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASS')
        db_name = os.environ.get('DB_NAME')
        db_host = os.environ.get('DB_HOST') # Será una ruta de socket unix
        # La conexión a Cloud SQL desde App Engine requiere un formato especial
        SQLALCHEMY_DATABASE_URI = (
            f'mysql+pymysql://{db_user}:{db_pass}@/{db_name}'
            f'?unix_socket={db_host}'
        )
    else:
        # Configuración para la base de datos local
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(basedir, 'app.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de Correo
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = [os.environ.get('ADMINS')]