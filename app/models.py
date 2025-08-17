from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class Cliente(db.Model):
    __tablename__ = 'clientes'
    rut = db.Column(db.String(10), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(15))
    direccion = db.Column(db.String(200))
    ciudad = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    patente = db.Column(db.String(8), primary_key=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(30))
    chasis_n = db.Column(db.String(100), unique=True, nullable=False)
    motor_n = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    metodo_pago = db.Column(db.Enum('contado', 'credito automotriz', 'T. crédito', 'T. débito', name='metodo_pago_enum'), nullable=False)
    detalles = db.Column(db.Text)
    total = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NotaVenta(db.Model):
    __tablename__ = 'notas_de_venta'
    id = db.Column(db.Integer, primary_key=True) # Folio
    cliente_rut = db.Column(db.String(10), db.ForeignKey('clientes.rut'), nullable=False)
    vehiculo_patente = db.Column(db.String(8), db.ForeignKey('vehiculos.patente'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pago_id = db.Column(db.Integer, db.ForeignKey('pagos.id'), unique=True, nullable=False)
    fecha_venta = db.Column(db.Date, nullable=False)
    monto_final = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Enum('completada', 'pendiente', 'anulada', name='estado_venta_enum'), default='pendiente', nullable=False)
    observaciones = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones para acceder a los objetos relacionados fácilmente
    cliente = db.relationship('Cliente', backref=db.backref('notas_venta', lazy='dynamic'))
    vehiculo = db.relationship('Vehiculo', backref=db.backref('notas_venta', lazy='dynamic'))
    vendedor = db.relationship('User', backref=db.backref('notas_venta', lazy='dynamic'))
    pago = db.relationship('Pago', uselist=False, backref=db.backref('nota_venta', lazy=True))
