from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

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
    def get_reset_password_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})
    @staticmethod
    def verify_reset_password_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
            user_id = data.get('user_id')
        except:
            return None
        return User.query.get(user_id)

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

    #FORMATEAR EL RUT
    def rut_formateado(self):
        """Devuelve el RUT con formato de puntos y guion."""
        rut = self.rut.replace(".", "").replace("-", "")
        if len(rut) < 2:
            return self.rut
        cuerpo = rut[:-1]
        dv = rut[-1]
        # Formatea el cuerpo del RUT con puntos
        cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".")
        return f"{cuerpo_formateado}-{dv}"
class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    patente = db.Column(db.String(8), primary_key=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(30))
    chasis_n = db.Column(db.String(100), unique=True, nullable=False)
    motor_n = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Integer, nullable=False) # Precio de Venta al Público
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), nullable=False, default='disponible')
    
    # --- NUEVOS CAMPOS DE CONSIGNACIÓN ---
    propietario_rut = db.Column(db.String(10), db.ForeignKey('clientes.rut'), nullable=True)
    kilometraje = db.Column(db.Integer, nullable=True)
    precio_acordado = db.Column(db.Integer, nullable=True) # Precio que pide el dueño
    # -------------------------------------
    
    tipo_adquisicion = db.Column(db.String(50), nullable=False, default='consignacion')
    costo_compra = db.Column(db.Integer, nullable=True, default=0) # Lo que pagó la automotora si es propio

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación para acceder a los datos del dueño fácilmente
    propietario = db.relationship('Cliente', backref=db.backref('vehiculos_consignados', lazy='dynamic'))

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
    estado = db.Column(db.Enum('completada', 'pendiente', 'anulada', 'reservada', name='estado_venta_enum'), default='pendiente', nullable=False)
    monto_reserva = db.Column(db.Integer, nullable=True) 
    dias_vigencia = db.Column(db.Integer, nullable=True)
    observaciones = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones para acceder a los objetos relacionados fácilmente
    cliente = db.relationship('Cliente', backref=db.backref('notas_venta', lazy='dynamic'))
    vehiculo = db.relationship('Vehiculo', backref=db.backref('notas_venta', lazy='dynamic'))
    vendedor = db.relationship('User', backref=db.backref('notas_venta', lazy='dynamic'))
    pago = db.relationship('Pago', uselist=False, backref=db.backref('nota_venta', lazy=True))




class RegistroHistorial(db.Model):
    __tablename__ = 'registro_historial'
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_patente = db.Column(db.String(10), db.ForeignKey('vehiculos.patente'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now)
    descripcion = db.Column(db.String(255), nullable=False)
    
    # Relación inversa (permite llamar vehiculo.registros)
    vehiculo = db.relationship('Vehiculo', backref=db.backref('registros', lazy='dynamic', order_by='RegistroHistorial.fecha.desc()'))