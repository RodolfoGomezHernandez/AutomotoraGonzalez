from app import create_app, db
from app.models import User, Cliente, Vehiculo, Pago, NotaVenta

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Permite acceder a modelos y db en la consola de Flask sin importarlos."""
    return {
        'db': db,
        'User': User,
        'Cliente': Cliente,
        'Vehiculo': Vehiculo,
        'Pago': Pago,
        'NotaVenta': NotaVenta
    }