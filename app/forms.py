from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import User, Cliente, Vehiculo
from wtforms import IntegerField, TextAreaField

class ClienteForm(FlaskForm):
    rut = StringField('RUT (ej: 12345678-9)', validators=[DataRequired(), Length(max=12)])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(max=100)])
    telefono = StringField('Teléfono', validators=[Length(max=15)])
    direccion = StringField('Dirección', validators=[Length(max=200)])
    ciudad = StringField('Ciudad', validators=[Length(max=100)])
    submit = SubmitField('Guardar Cliente')

    def validate_rut(self, rut):
        # Limpia el RUT para la validación y almacenamiento
        rut_limpio = rut.data.replace(".", "").replace("-", "").lower()
        if not rut_limpio[:-1].isdigit() or not rut_limpio[-1] in '0123456789k':
             raise ValidationError('RUT inválido. Use solo números y K si corresponde.')
        
        # Valida contra la base de datos usando el RUT limpio
        cliente = Cliente.query.get(rut_limpio)
        if cliente:
            raise ValidationError('Este RUT ya está registrado.')

class VehiculoForm(FlaskForm):
    patente = StringField('Patente', validators=[DataRequired(), Length(max=8)])
    marca = StringField('Marca', validators=[DataRequired(), Length(max=50)])
    modelo = StringField('Modelo', validators=[DataRequired(), Length(max=50)])
    ano = IntegerField('Año', validators=[DataRequired()])
    color = StringField('Color', validators=[Length(max=30)])
    chasis_n = StringField('N° Chasis', validators=[DataRequired(), Length(max=100)])
    motor_n = StringField('N° Motor', validators=[DataRequired(), Length(max=100)])
    valor = IntegerField('Valor', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción')
    submit = SubmitField('Guardar Vehículo')

    def validate_patente(self, patente):
        vehiculo = Vehiculo.query.get(patente.data)
        if vehiculo:
            raise ValidationError('Esta patente ya está registrada.')

    def validate_chasis_n(self, chasis_n):
        vehiculo = Vehiculo.query.filter_by(chasis_n=chasis_n.data).first()
        if vehiculo:
            raise ValidationError('Este número de chasis ya está registrado.')

    def validate_motor_n(self, motor_n):
        vehiculo = Vehiculo.query.filter_by(motor_n=motor_n.data).first()
        if vehiculo:
            raise ValidationError('Este número de motor ya está registrado.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email("Email inválido.")])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recuérdame')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    name = StringField('Nombre Completo', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email("Email inválido.")])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8, message="La contraseña debe tener al menos 8 caracteres.")])
    password2 = PasswordField(
        'Repetir Contraseña', validators=[DataRequired(), EqualTo('password', message="Las contraseñas deben coincidir.")])
    submit = SubmitField('Registrar')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Este email ya está registrado. Por favor, use uno diferente.')

class NotaVentaForm(FlaskForm):
    cliente_rut = StringField('RUT Cliente', validators=[DataRequired(), Length(max=10)])
    vehiculo_patente = StringField('Patente Vehículo', validators=[DataRequired(), Length(max=8)])
    fecha_venta = DateField('Fecha de Venta', format='%Y-%m-%d', validators=[DataRequired()])
    monto_final = IntegerField('Monto Final', validators=[DataRequired()])
    metodo_pago = SelectField('Método de Pago', choices=[
        ('contado', 'Contado'),
        ('credito automotriz', 'Crédito Automotriz'),
        ('T. crédito', 'Tarjeta de Crédito'),
        ('T. débito', 'Tarjeta de Débito')
    ], validators=[DataRequired()])
    estado = SelectField('Estado', choices=[
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('anulada', 'Anulada')
    ], validators=[DataRequired()])
    observaciones = TextAreaField('Observaciones')
    submit = SubmitField('Guardar Nota de Venta')

    def validate_cliente_rut(self, cliente_rut):
        if not Cliente.query.get(cliente_rut.data):
            raise ValidationError('Este RUT de cliente no existe en la base de datos.')

    def validate_vehiculo_patente(self, vehiculo_patente):
        if not Vehiculo.query.get(vehiculo_patente.data):
            raise ValidationError('Esta patente de vehículo no existe en la base de datos.')
