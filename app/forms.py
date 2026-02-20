from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import User, Cliente, Vehiculo
from wtforms.validators import DataRequired, Length, Optional

# ... dentro de tu VehiculoForm ...
propietario_rut = StringField('RUT Propietario', validators=[Optional(), Length(max=12)])
precio_acordado = IntegerField('Precio Acordado con Dueño $', validators=[Optional()], default=0)
costo_compra = IntegerField('Costo de Compra Propia $', validators=[Optional()], default=0)
class ClienteForm(FlaskForm):
    rut = StringField('RUT (ej: 12345678-9)', validators=[DataRequired(), Length(max=12)])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(max=100)])
    telefono = StringField('Teléfono', validators=[Length(max=15)])
    direccion = StringField('Dirección', validators=[Length(max=200)])
    ciudad = StringField('Ciudad', validators=[Length(max=100)])
    submit = SubmitField('Guardar Cliente')

    def validate_rut(self, rut):
        # Limpia el RUT para la validación (Módulo 11)
        rut_limpio = rut.data.replace(".", "").replace("-", "").upper()
        if len(rut_limpio) < 2:
            raise ValidationError('RUT demasiado corto.')
            
        cuerpo = rut_limpio[:-1]
        dv_ingresado = rut_limpio[-1]

        if not cuerpo.isdigit() or dv_ingresado not in '0123456789K':
             raise ValidationError('RUT inválido. Use solo números y K si corresponde.')
        
        suma = 0
        multiplo = 2
        for caracter in reversed(cuerpo):
            suma += int(caracter) * multiplo
            multiplo += 1
            if multiplo == 8:
                multiplo = 2
                
        resto = suma % 11
        dv_calculado = 11 - resto
        
        if dv_calculado == 11:
            dv_esperado = '0'
        elif dv_calculado == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(dv_calculado)

        if dv_ingresado != dv_esperado:
            raise ValidationError('RUT inválido. El dígito verificador no es correcto matemáticamente.')

        # Valida contra la base de datos (tu BD guarda en minúsculas)
        cliente = Cliente.query.get(rut_limpio.lower())
        if cliente:
            raise ValidationError('Este RUT ya está registrado en el sistema.')

class VehiculoForm(FlaskForm):
    patente = StringField('Patente', validators=[DataRequired(), Length(max=8)])
    tipo_adquisicion = SelectField('Tipo de Adquisición', choices=[
        ('consignacion', 'Consignación (De un tercero)'),
        ('compra_directa', 'Compra Directa (Vehículo Propio)')
    ], validators=[DataRequired()])
    costo_compra = IntegerField('Costo de Compra Propia $', validators=[Optional()], default=0)
    propietario_rut = StringField('RUT Propietario', validators=[Optional(), Length(max=12)])
    kilometraje = IntegerField('Kilometraje', validators=[DataRequired()])
    precio_acordado = IntegerField('Precio Acordado con Dueño $', validators=[Optional()], default=0)
    marca = StringField('Marca', validators=[DataRequired(), Length(max=50)])
    modelo = StringField('Modelo', validators=[DataRequired(), Length(max=50)])
    ano = IntegerField('Año', validators=[DataRequired()])
    color = StringField('Color', validators=[Length(max=30)])
    chasis_n = StringField('N° Chasis', validators=[DataRequired(), Length(max=100)])
    motor_n = StringField('N° Motor', validators=[DataRequired(), Length(max=100)])
    valor = IntegerField('Valor de Venta en Automotora ($)', validators=[DataRequired()])
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
            
    def validate_propietario_rut(self, propietario_rut):
        rut_limpio = propietario_rut.data.replace(".", "").replace("-", "").lower()
        if not Cliente.query.get(rut_limpio):
            raise ValidationError('Este RUT no está en la base de datos. Por favor, registre al Cliente primero.')

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
    cliente_rut = StringField('RUT Cliente', validators=[DataRequired(), Length(max=12)])
    vehiculo_patente = StringField('Patente Vehículo', validators=[DataRequired(), Length(max=8)])
    fecha_venta = DateField('Fecha de Venta', format='%Y-%m-%d', validators=[DataRequired()])
    monto_final = IntegerField('Monto Final', validators=[DataRequired()])
    metodo_pago = SelectField('Método de Pago', choices=[
        ('contado', 'Contado'),
        ('credito automotriz', 'Crédito Automotriz'),
        ('T. crédito', 'Tarjeta de Crédito'),
        ('T. débito', 'Tarjeta de Débito')
    ], validators=[DataRequired()])
    monto_reserva = IntegerField('Monto de Reserva', default=0)
    dias_vigencia = IntegerField('Días de Vigencia de Reserva', default=0)
    estado = SelectField('Estado', choices=[
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('anulada', 'Anulada'),
        ('reservada', 'Reservada')
    ], validators=[DataRequired()])
    observaciones = TextAreaField('Observaciones')
    submit = SubmitField('Guardar Nota de Venta')

    def __init__(self, *args, **kwargs):
        self.nota_id = kwargs.pop('nota_id', None)
        super(NotaVentaForm, self).__init__(*args, **kwargs)

    def validate_cliente_rut(self, cliente_rut):
        rut_limpio = cliente_rut.data.replace(".", "").replace("-", "").lower()
        if not Cliente.query.get(rut_limpio):
            raise ValidationError('Este RUT de cliente no existe en la base de datos.')

    def validate_vehiculo_patente(self, vehiculo_patente):
        vehiculo = Vehiculo.query.get(vehiculo_patente.data)
        if not vehiculo:
            raise ValidationError('Esta patente de vehículo no existe en la base de datos.')
        
        # Si está disponible, lo permite
        if vehiculo.estado == 'disponible':
            return
            
        # Si NO está disponible, revisamos si es el vehículo de la nota que estamos editando
        if self.nota_id:
            from app.models import NotaVenta # Importación local
            from app import db
            nota_actual = db.session.get(NotaVenta, self.nota_id)

            if nota_actual and nota_actual.vehiculo_patente == vehiculo.patente:
                return 
                
        raise ValidationError('Este vehículo ya está reservado o vendido.')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Reseteo de Contraseña')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva Contraseña', validators=[DataRequired()])
    password2 = PasswordField(
        'Repetir Nueva Contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Resetear Contraseña')