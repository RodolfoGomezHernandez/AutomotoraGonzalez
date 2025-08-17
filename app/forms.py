from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import User, Cliente, Vehiculo

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
