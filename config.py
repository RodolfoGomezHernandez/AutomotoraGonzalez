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
        # --- CONFIGURACIÓN PARA PRODUCCIÓN EN GOOGLE CLOUD ---
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASS')
        db_name = os.environ.get('DB_NAME')
        db_host = os.environ.get('DB_HOST')

        # Si DB_HOST es una ruta de socket (desde App Engine)
        if db_host and db_host.startswith('/cloudsql'):
            db_socket_dir = '/cloudsql'
            cloud_sql_connection_name = db_host.split('/')[-1]
            SQLALCHEMY_DATABASE_URI = (
                f'mysql+pymysql://{db_user}:{db_pass}@/{db_name}'
                f'?unix_socket={db_socket_dir}/{cloud_sql_connection_name}'
            )
        # Si DB_HOST es una IP (desde Cloud Shell con Proxy)
        else:
            SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'
    else:
        # --- CONFIGURACIÓN PARA DESARROLLO LOCAL ---
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