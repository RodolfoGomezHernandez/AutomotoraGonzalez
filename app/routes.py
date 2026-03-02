from flask import render_template, request, flash, redirect, url_for, Blueprint, make_response, abort, current_app
from flask_login import login_required, current_user
from app import db
from sqlalchemy import or_, cast, String, Date, func
from sqlalchemy.exc import IntegrityError
from fpdf import FPDF
import os
from datetime import date, datetime
from .models import NotaVenta, Cliente, Vehiculo, Pago
from .forms import NotaVentaForm, ClienteForm, VehiculoForm
from .models import RegistroHistorial
bp = Blueprint('main', __name__)

# --- DASHBOARD ---
@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # 1. Configurar Fechas (Por defecto: Mes actual)
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)
    
    fecha_inicio_str = request.args.get('fecha_inicio', inicio_mes.strftime('%Y-%m-%d'))
    fecha_fin_str = request.args.get('fecha_fin', hoy.strftime('%Y-%m-%d'))
    
    fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
    fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

    # 2. KPIs Generales Estáticos (Inventario)
    total_vehiculos = Vehiculo.query.count()
    disponibles = Vehiculo.query.filter_by(estado='disponible').count()
    
    # 3. Datos del periodo seleccionado
    notas_periodo = NotaVenta.query.filter(
        NotaVenta.fecha_venta >= fecha_inicio,
        NotaVenta.fecha_venta <= fecha_fin,
        NotaVenta.estado == 'completada'
    ).all()
    
    vehiculos_vendidos_periodo = len(notas_periodo)
    
    # Variables para los cálculos
    ingreso_real_total = 0
    ventas_por_fecha = {}
    ingresos_por_fecha = {}
    ventas_por_adquisicion = {'consignacion': 0, 'compra_directa': 0}
    marcas_vendidas = {}

    # 4. Procesar cada venta completada
    for nota in notas_periodo:
        vehiculo = nota.vehiculo
        if not vehiculo: continue 
        
        fecha_str = nota.fecha_venta.strftime('%d-%m-%Y')
        
        # CÁLCULO DE GANANCIA REAL
        ingreso_nota = 0
        if vehiculo.tipo_adquisicion == 'compra_directa':
            ingreso_nota = nota.monto_final - (vehiculo.costo_compra or 0)
        else:
            # Consignación: 3% o $200.000 mínimo
            ingreso_nota = max(nota.monto_final * 0.03, 200000)
        
        ingreso_real_total += ingreso_nota
        
        # Agrupar para los gráficos
        ventas_por_fecha[fecha_str] = ventas_por_fecha.get(fecha_str, 0) + 1
        ingresos_por_fecha[fecha_str] = ingresos_por_fecha.get(fecha_str, 0) + ingreso_nota
        
        tipo = vehiculo.tipo_adquisicion or 'consignacion'
        ventas_por_adquisicion[tipo] = ventas_por_adquisicion.get(tipo, 0) + 1
        
        marcas_vendidas[vehiculo.marca] = marcas_vendidas.get(vehiculo.marca, 0) + 1

    # Formatear dinero para la vista
    ingreso_formateado = "${:,.0f}".format(ingreso_real_total).replace(',', '.')

    # Ordenar datos de fechas cronológicamente
    fechas_ordenadas = sorted(ventas_por_fecha.keys(), key=lambda x: datetime.strptime(x, '%d-%m-%Y'))
    grafico_ventas_data = [ventas_por_fecha[f] for f in fechas_ordenadas]
    grafico_ingresos_data = [ingresos_por_fecha[f] for f in fechas_ordenadas]

    return render_template('index.html', title='Dashboard',
                           fecha_inicio=fecha_inicio_str,
                           fecha_fin=fecha_fin_str,
                           total_vehiculos=total_vehiculos,
                           disponibles=disponibles,
                           vendidos=vehiculos_vendidos_periodo,
                           ingreso_formateado=ingreso_formateado,
                           fechas_labels=fechas_ordenadas,
                           grafico_ventas_data=grafico_ventas_data,
                           grafico_ingresos_data=grafico_ingresos_data,
                           marcas_labels=list(marcas_vendidas.keys()),
                           marcas_data=list(marcas_vendidas.values()),
                           adquisicion_labels=['Consignación', 'Compra Directa'],
                           adquisicion_data=[ventas_por_adquisicion.get('consignacion', 0), ventas_por_adquisicion.get('compra_directa', 0)])
# --- RUTAS DE NOTAS DE VENTA ---
@bp.route('/notas-venta')
@login_required
def listar_notas_venta():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search_field = request.args.get('search_field', 'todos')
    search_query = request.args.get('q', '', type=str)

    if per_page not in [20, 30, 50]:
        per_page = 20
    
    # Usamos outerjoin para asegurar que siempre se muestren las notas
    query = NotaVenta.query.outerjoin(Cliente).outerjoin(Vehiculo)

    if search_query:
        search_term = f"%{search_query}%"
        
        if search_field == 'folio':
            query = query.filter(cast(NotaVenta.id, String).like(search_term))
        elif search_field == 'cliente':
            query = query.filter(or_(Cliente.nombre.like(search_term), Cliente.apellido.like(search_term), Cliente.rut.like(search_term)))
        elif search_field == 'vehiculo':
            query = query.filter(or_(Vehiculo.marca.like(search_term), Vehiculo.modelo.like(search_term), Vehiculo.patente.like(search_term)))
        elif search_field == 'estado':
            query = query.filter(NotaVenta.estado.like(search_term))
        else:
            query = query.filter(or_(
                cast(NotaVenta.id, String).like(search_term),
                Cliente.nombre.like(search_term),
                Cliente.apellido.like(search_term),
                Cliente.rut.like(search_term),
                Vehiculo.marca.like(search_term),
                Vehiculo.modelo.like(search_term),
                Vehiculo.patente.like(search_term),
                NotaVenta.estado.like(search_term)
            ))

    # Ordenamos por el ID de mayor a menor para garantizar la secuencia de ingreso real
    notas = query.order_by(NotaVenta.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    
    )
    
    return render_template(
        'notas_venta/listar.html',
        title='Notas de Venta',
        notas=notas, 
        per_page=per_page,
        search_query=search_query,
        search_field=search_field
    )


@bp.route('/notas-venta/crear', methods=['GET', 'POST'])
@login_required
def crear_nota_venta():
    form = NotaVentaForm()
    if form.validate_on_submit():
        try:
            vehiculo = Vehiculo.query.get(form.vehiculo_patente.data)

            pago = Pago(metodo_pago=form.metodo_pago.data, total=form.monto_final.data)
            db.session.add(pago)
            db.session.flush()

            nota = NotaVenta(
                cliente_rut=form.cliente_rut.data,
                vehiculo_patente=form.vehiculo_patente.data,
                user_id=current_user.id,
                pago_id=pago.id,
                fecha_venta=form.fecha_venta.data,
                monto_final=form.monto_final.data,
                estado=form.estado.data,
                observaciones=form.observaciones.data,
                monto_reserva=form.monto_reserva.data if form.estado.data == 'reservada' else 0,
                dias_vigencia=form.dias_vigencia.data if form.estado.data == 'reservada' else 0
            )
            db.session.add(nota)

            vehiculo.estado = 'reservado' if form.estado.data == 'reservada' else 'vendido'
            db.session.add(vehiculo)
            db.session.flush() # Para obtener el ID de la nota recién creada
            evento = RegistroHistorial(
                vehiculo_patente=vehiculo.patente, 
                descripcion=f"Se creó la Nota de Venta #{nota.id} en estado '{form.estado.data}'."
            )
            db.session.add(evento)
            db.session.commit()
            flash('Nota de venta creada exitosamente.', 'success')
            return redirect(url_for('main.listar_notas_venta'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado: {e}', 'danger')
    return render_template('notas_venta/crear_editar.html', title='Crear Nota de Venta', form=form)


@bp.route('/notas-venta/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_nota_venta(id):
    nota = db.session.get(NotaVenta, id) or abort(404)
    form = NotaVentaForm(obj=nota, nota_id=nota.id) 
    
    if form.validate_on_submit():
        try:
            vehiculo = Vehiculo.query.get(form.vehiculo_patente.data)

            # 1. Guardar el estado antiguo
            estado_antiguo = nota.estado

            nota.cliente_rut = form.cliente_rut.data
            nota.vehiculo_patente = form.vehiculo_patente.data
            nota.fecha_venta = form.fecha_venta.data
            nota.monto_final = form.monto_final.data
            nota.estado = form.estado.data
            nota.observaciones = form.observaciones.data
            
            nota.monto_reserva = form.monto_reserva.data or 0
            nota.dias_vigencia = form.dias_vigencia.data or 0

            if nota.pago:
                nota.pago.metodo_pago = form.metodo_pago.data
                nota.pago.total = form.monto_final.data

            if form.estado.data == 'completada':
                vehiculo.estado = 'vendido'
            elif form.estado.data == 'anulada':
                vehiculo.estado = 'disponible'
            elif form.estado.data == 'reservada':
                vehiculo.estado = 'reservado'
            elif form.estado.data == 'pendiente':
                vehiculo.estado = 'vendido'

            # 2. Registrar en la bitácora si hubo cambio de estado
            if estado_antiguo != form.estado.data:
                evento = RegistroHistorial(
                    vehiculo_patente=vehiculo.patente, 
                    descripcion=f"Nota de Venta #{nota.id} cambió de '{estado_antiguo}' a '{form.estado.data}'."
                )
                db.session.add(evento)

            db.session.commit()
            flash('Nota de venta actualizada con éxito.', 'success')
            return redirect(url_for('main.listar_notas_venta'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la nota de venta: {e}', 'danger')
            
    form.cliente_rut.data = nota.cliente_rut
    form.vehiculo_patente.data = nota.vehiculo_patente
    form.fecha_venta.data = nota.fecha_venta
    form.monto_final.data = nota.monto_final
    form.estado.data = nota.estado
    form.observaciones.data = nota.observaciones
    form.monto_reserva.data = nota.monto_reserva
    form.dias_vigencia.data = nota.dias_vigencia
    if nota.pago:
        form.metodo_pago.data = nota.pago.metodo_pago
        
    return render_template('notas_venta/crear_editar.html', title='Editar Nota de Venta', form=form, nota_id=id)


@bp.route('/notas-venta/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_nota_venta(id):
    nota = db.session.get(NotaVenta, id) or abort(404)
    try:
        pago = nota.pago
        db.session.delete(nota)
        if pago:
            db.session.delete(pago)
        db.session.commit()
        flash('Nota de venta eliminada con éxito.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la nota de venta: {e}', 'danger')
    return redirect(url_for('main.listar_notas_venta'))

# --- RUTAS DE CLIENTES ---
@bp.route('/clientes')
@login_required
def listar_clientes():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    query = Cliente.query
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(or_(
            Cliente.rut.like(search_term),
            Cliente.nombre.like(search_term),
            Cliente.apellido.like(search_term)
        ))
    clientes = query.order_by(Cliente.nombre).paginate(page=page, per_page=15)
    return render_template('listar_clientes.html', title='Listado de Clientes', clientes=clientes, search_query=search_query)

@bp.route('/clientes/crear', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        rut_limpio = form.rut.data.replace(".", "").replace("-", "").lower()
        cliente = Cliente(
            rut=rut_limpio,
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            telefono=form.telefono.data,
            direccion=form.direccion.data,
            ciudad=form.ciudad.data
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente añadido con éxito.', 'success')
        return redirect(url_for('main.listar_clientes'))
    return render_template('crear_editar_simple.html', title='Añadir Nuevo Cliente', form=form)

@bp.route('/clientes/editar/<rut>', methods=['GET', 'POST'])
@login_required
def editar_cliente(rut):
    cliente = Cliente.query.get_or_404(rut)
    form = ClienteForm(original_rut=cliente.rut, obj=cliente)
    if form.validate_on_submit():
        rut_limpio = form.rut.data.replace(".", "").replace("-", "").lower()
        cliente.rut = rut_limpio
        cliente.nombre = form.nombre.data
        cliente.apellido = form.apellido.data
        cliente.telefono = form.telefono.data
        cliente.direccion = form.direccion.data
        cliente.ciudad = form.ciudad.data
        db.session.commit()
        flash('Cliente actualizado con éxito.', 'success')
        return redirect(url_for('main.listar_clientes'))
    form.rut.data = cliente.rut_formateado()
    return render_template('crear_editar_simple.html', title='Editar Cliente', form=form)

@bp.route('/clientes/eliminar/<rut>', methods=['POST'])
@login_required
def eliminar_cliente(rut):
    cliente = Cliente.query.get_or_404(rut)
    if cliente.notas_venta.first():
        flash('No se puede eliminar un cliente con notas de venta asociadas.', 'danger')
        return redirect(url_for('main.listar_clientes'))
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente eliminado con éxito.', 'success')
    return redirect(url_for('main.listar_clientes'))

# --- RUTAS DE VEHÍCULOS ---
@bp.route('/vehiculos')
@login_required
def listar_vehiculos():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    query = Vehiculo.query.filter_by(estado='disponible')
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(or_(
            Vehiculo.patente.like(search_term),
            Vehiculo.marca.like(search_term),
            Vehiculo.modelo.like(search_term)
        ))
    vehiculos = query.order_by(Vehiculo.marca).paginate(page=page, per_page=15)
    return render_template('listar_vehiculos.html', title='Listado de Vehículos', vehiculos=vehiculos, search_query=search_query)

@bp.route('/vehiculos/vendidos')
@login_required
def listar_vehiculos_vendidos():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    # Empezar la consulta solo con los vendidos
    query = Vehiculo.query.filter_by(estado='vendido')

    # Si hay texto en el buscador, filtrar
    if search:
        query = query.filter(
            (Vehiculo.patente.ilike(f'%{search}%')) |
            (Vehiculo.marca.ilike(f'%{search}%')) |
            (Vehiculo.modelo.ilike(f'%{search}%'))
        )

    # Ordenar por fecha de creación (del más reciente al más antiguo)
    vehiculos = query.order_by(Vehiculo.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    
    
    # Agregamos search=search al final
    return render_template('listar_vehiculos_vendidos.html', title='Historial de Vehículos Vendidos', vehiculos=vehiculos, search=search)



@bp.route('/vehiculos/relistar/<patente>', methods=['POST'])
@login_required
def relistar_vehiculo(patente):
    vehiculo = Vehiculo.query.get_or_404(patente)
    vehiculo.estado = 'disponible'
    db.session.commit()
    flash(f'El vehículo {vehiculo.patente} ha sido puesto a la venta nuevamente.', 'success')
    return redirect(url_for('main.listar_vehiculos_vendidos'))

@bp.route('/vehiculos/crear', methods=['GET', 'POST'])
@login_required
def crear_vehiculo():
    form = VehiculoForm()
    if form.validate_on_submit():
        rut_limpio = form.propietario_rut.data.replace(".", "").replace("-", "").lower()
        
        vehiculo = Vehiculo(
            patente=form.patente.data,
            tipo_adquisicion=form.tipo_adquisicion.data, 
            costo_compra=form.costo_compra.data,
            marca=form.marca.data,
            modelo=form.modelo.data,
            ano=form.ano.data,
            color=form.color.data,
            chasis_n=form.chasis_n.data,
            motor_n=form.motor_n.data,
            valor=form.valor.data,
            descripcion=form.descripcion.data,
            propietario_rut=rut_limpio,
            kilometraje=form.kilometraje.data,
            precio_acordado=form.precio_acordado.data,
        )
        db.session.add(vehiculo)
        db.session.commit()
        flash('Vehículo añadido con éxito.', 'success')
        return redirect(url_for('main.listar_vehiculos'))
    return render_template('crear_editar_simple.html', title='Añadir Nuevo Vehículo', form=form)

@bp.route('/vehiculos/editar/<patente>', methods=['GET', 'POST'])
@login_required
def editar_vehiculo(patente):
    vehiculo = Vehiculo.query.get_or_404(patente)
    form = VehiculoForm(original_patente=vehiculo.patente, original_chasis_n=vehiculo.chasis_n, original_motor_n=vehiculo.motor_n, obj=vehiculo)
    
    if form.validate_on_submit():
        rut_limpio = form.propietario_rut.data.replace(".", "").replace("-", "").lower()
        vehiculo.tipo_adquisicion = form.tipo_adquisicion.data
        vehiculo.costo_compra = form.costo_compra.data
        vehiculo.propietario_rut = rut_limpio
        vehiculo.kilometraje = form.kilometraje.data
        vehiculo.precio_acordado = form.precio_acordado.data
        vehiculo.patente = form.patente.data
        vehiculo.marca = form.marca.data
        vehiculo.modelo = form.modelo.data
        vehiculo.ano = form.ano.data
        vehiculo.color = form.color.data
        vehiculo.chasis_n = form.chasis_n.data
        vehiculo.motor_n = form.motor_n.data
        vehiculo.valor = form.valor.data
        vehiculo.descripcion = form.descripcion.data
        db.session.commit()
        flash('Vehículo actualizado con éxito.', 'success')
        return redirect(url_for('main.listar_vehiculos'))
        vehiculo.tipo_adquisicion = form.tipo_adquisicion.data
        vehiculo.costo_compra = form.costo_compra.data
    return render_template('crear_editar_simple.html', title='Editar Vehículo', form=form)


@bp.route('/vehiculos/eliminar/<patente>', methods=['POST'])
@login_required
def eliminar_vehiculo(patente):
    vehiculo = Vehiculo.query.get_or_404(patente)
    if vehiculo.notas_venta.first():
        flash('No se puede eliminar un vehículo con notas de venta asociadas.', 'danger')
        return redirect(url_for('main.listar_vehiculos'))
    db.session.delete(vehiculo)
    db.session.commit()
    flash('Vehículo eliminado con éxito.', 'success')
    return redirect(url_for('main.listar_vehiculos'))

# --- RUTAS DE PDF ---
class PDF(FPDF):
    def header(self):
        # Ajustado para que encuentre el logo sin problemas
        logo_path = os.path.join(current_app.static_folder, 'img', 'logo.png')
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 33)
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Nota de Venta', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')
        self.cell(0, 10, 'Automotora Gonzalez | Gracias por su compra.', 0, 0, 'R')

@bp.route('/notas-venta/pdf/<int:id>')
@login_required
def generar_pdf(id):
    nota = db.session.get(NotaVenta, id) or abort(404)
    
    pdf = PDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Folio: #{nota.id}", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Fecha de Venta: {nota.fecha_venta.strftime('%d-%m-%Y')}", 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(230, 245, 230)
    pdf.cell(95, 10, 'Datos del Cliente', 1, 0, 'C', fill=True)
    pdf.cell(95, 10, 'Datos del Vendedor', 1, 1, 'C', fill=True)
    
    pdf.set_font('Arial', '', 10)
    
    # --- VARIABLES PROTEGIDAS ---
    nombre_cliente = f"{nota.cliente.nombre} {nota.cliente.apellido}" if nota.cliente else "Cliente Borrado"
    rut_cliente = nota.cliente.rut_formateado() if nota.cliente else "N/A"
    telefono_cliente = nota.cliente.telefono if nota.cliente else "N/A"
    direccion_cliente = f"{nota.cliente.direccion}, {nota.cliente.ciudad}" if nota.cliente else "N/A"

    pdf.cell(95, 7, f"Nombre: {nombre_cliente}", 1, 0)
    pdf.cell(95, 7, f"Nombre: {nota.vendedor.name}", 1, 1)
    pdf.cell(95, 7, f"RUT: {rut_cliente}", 1, 0)
    pdf.cell(95, 7, f"Email: {nota.vendedor.email}", 1, 1)
    pdf.cell(95, 7, f"Telefono: {telefono_cliente}", 1, 0)
    pdf.cell(95, 7, "", 1, 1) 
    pdf.cell(0, 7, f"Direccion: {direccion_cliente}", 1, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Detalles del Vehiculo', 1, 1, 'C', fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f"Patente: {nota.vehiculo.patente}", 1, 0)
    pdf.cell(95, 7, f"Marca / Modelo: {nota.vehiculo.marca} {nota.vehiculo.modelo}", 1, 1)
    pdf.cell(95, 7, f"Ano: {nota.vehiculo.ano}", 1, 0)
    pdf.cell(95, 7, f"N Chasis: {nota.vehiculo.chasis_n}", 1, 1)
    pdf.cell(95, 7, f"N Motor: {nota.vehiculo.motor_n}", 1, 0)
    pdf.cell(95, 7, "", 1, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Condiciones de la Venta', 1, 1, 'C', fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 7, f"Metodo de Pago: {nota.pago.metodo_pago.capitalize()}", 1, 1)

    x = pdf.get_x()
    y = pdf.get_y()
    pdf.rect(x, y, 190, 30) 
    pdf.set_xy(x + 2, y + 2)
    pdf.multi_cell(186, 5, f"Observaciones: {nota.observaciones or 'Sin observaciones.'}", 0)
    
    pdf.set_xy(x, y + 30)

    pdf.set_font('Arial', 'B', 12) 
    monto_formateado = "${:,.0f}".format(nota.monto_final).replace(',', '.')
    monto_reserva = nota.monto_reserva or 0
    saldo_pendiente = nota.monto_final - monto_reserva
    
    monto_res_formateado = "${:,.0f}".format(monto_reserva).replace(',', '.')
    saldo_formateado = "${:,.0f}".format(saldo_pendiente).replace(',', '.')
    
    if nota.estado == 'reservada':
        pdf.cell(0, 8, f"Monto Total Vehiculo: {monto_formateado}", 1, 1, 'R')
        pdf.cell(0, 8, f"Abono de Reserva: {monto_res_formateado}", 1, 1, 'R')
        pdf.cell(0, 8, f"Saldo Pendiente a Pagar: {saldo_formateado}", 1, 1, 'R')
    elif nota.estado == 'completada' and monto_reserva > 0:
        pdf.cell(0, 8, f"Monto Total Vehiculo: {monto_formateado}", 1, 1, 'R')
        pdf.cell(0, 8, f"Abono Previo de Reserva: {monto_res_formateado}", 1, 1, 'R')
        pdf.cell(0, 8, f"Total Pagado en este Acto: {saldo_formateado}", 1, 1, 'R')
    else:
        pdf.cell(0, 8, f"Monto Final Pagado: {monto_formateado}", 1, 1, 'R')

    pdf.ln(5)
    pdf.set_font('Arial', '', 9)
    texto_legal = ("El vehiculo es usado y se hace entrega en este acto, en las condiciones mecanicas y de carroceria en que se encuentra y es conocido por el comprador recibiendolo este conforme, por tanto no acoge a ningun reclamo posterior. Ademas ha sido completamente revisado por el comprador o un mecanico de su confianza, liberando de toda responsabilidad a Automotora Gonzalez ya que esta actua solo como comisionista. Los costos de transferencia son de cargo exclusivo del comprador y la documentacion debe efectuarse dentro de los 30 dias de la adquisicion y PARA CONFORMIDAD FIRMAN este recibo.")
    pdf.multi_cell(0, 4, texto_legal)
    
    pdf.ln(15)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(90, 5, "___________________________________", 0, 0, 'C')
    pdf.cell(90, 5, "___________________________________", 0, 1, 'C')
    pdf.cell(90, 5, "Firma Cliente", 0, 0, 'C')
    pdf.cell(90, 5, "Firma Automotora", 0, 1, 'C')

    if nota.estado == 'reservada':
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'CONDICIONES DE LA RESERVA', 0, 1, 'C')
        pdf.ln(5)
        
        pdf.set_font('Arial', '', 11)
        condiciones = [
            f"1. La reserva tendra una vigencia de {nota.dias_vigencia or 0} dias corridos desde la fecha de firma del presente documento.",
            "2. Durante el periodo de reserva, la automotora se compromete a no ofrecer ni vender el vehiculo a terceros.",
            "3. En caso de que el cliente desista de la compra por cualquier motivo, o no concrete la operacion dentro del plazo acordado, la suma entregada en reserva NO sera devuelta, quedando a beneficio de la automotora en compensacion por concepto de gastos administrativos, tiempo de publicacion y perdida de oportunidad de venta.",
            "4. En caso de que la automotora no pueda concretar la venta por causas imputables exclusivamente a ella, el monto de la reserva sera devuelto integramente al cliente."
        ]
        
        for condicion in condiciones:
            pdf.multi_cell(0, 6, condicion)
            pdf.ln(3)
            
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'ACEPTACION', 0, 1, 'L')
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 6, "El cliente declara haber revisado el vehiculo y aceptar su estado general, asi como las condiciones senaladas en este documento. Firman en senal de conformidad:")
        
        pdf.ln(35)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(90, 5, "___________________________________", 0, 0, 'C')
        pdf.cell(90, 5, "___________________________________", 0, 1, 'C')
        pdf.cell(90, 5, "Firma Cliente", 0, 0, 'C')
        pdf.cell(90, 5, "Firma Automotora", 0, 1, 'C')

    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=nota_venta_{nota.id}.pdf'
    return response

@bp.route('/notas-venta/pdf-devolucion/<int:id>')
@login_required
def generar_pdf_devolucion(id):
    nota = db.session.get(NotaVenta, id) or abort(404)
    
    if nota.estado != 'anulada':
        flash('Solo se pueden generar comprobantes de devolución para notas anuladas.', 'warning')
        return redirect(url_for('main.listar_notas_venta'))
        
    pdf = PDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'COMPROBANTE DE DEVOLUCION DE RESERVA', 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"Folio Original: #{nota.id}", 0, 1)
    # CORRECCIÓN: Solo datetime.now()
    pdf.cell(0, 8, f"Fecha de Emision: {datetime.now().strftime('%d-%m-%Y')}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Datos del Cliente y Vehiculo', 1, 1, 'C', fill=True)
    pdf.set_font('Arial', '', 11)

    # PROTECCIÓN: Variables seguras
    nombre_cliente = f"{nota.cliente.nombre} {nota.cliente.apellido}" if nota.cliente else "Cliente Borrado"
    rut_cliente = nota.cliente.rut_formateado() if nota.cliente else "N/A"
    marca_modelo = f"{nota.vehiculo.marca} {nota.vehiculo.modelo}" if nota.vehiculo else "N/A"
    patente = nota.vehiculo.patente if nota.vehiculo else "N/A"

    pdf.cell(0, 8, f"Cliente: {nombre_cliente} (RUT: {rut_cliente})", 1, 1)
    pdf.cell(0, 8, f"Vehiculo: {marca_modelo} (Patente: {patente})", 1, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Detalle de la Devolucion', 1, 1, 'C', fill=True)
    pdf.set_font('Arial', '', 11)
    
    monto_res_formateado = "${:,.0f}".format(nota.monto_reserva or 0).replace(',', '.')
    
    texto_devolucion = (
        f"Mediante el presente documento, Automotora Gonzalez deja constancia de la anulacion de la reserva "
        f"correspondiente al folio #{nota.id}.\n\n"
        f"Se realiza la devolucion integra del dinero abonado en concepto de reserva por un monto de "
        f"{monto_res_formateado}, liberando a ambas partes de cualquier obligacion futura respecto a "
        f"la compra de este vehiculo."
    )
    pdf.multi_cell(0, 8, texto_devolucion, 1)
    pdf.ln(20)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(90, 5, "___________________________________", 0, 0, 'C')
    pdf.cell(90, 5, "___________________________________", 0, 1, 'C')
    pdf.cell(90, 5, "Firma Cliente (Recibi Conforme)", 0, 0, 'C')
    pdf.cell(90, 5, "Firma Automotora", 0, 1, 'C')
    
    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=devolucion_reserva_{nota.id}.pdf'
    return response

@bp.route('/vehiculos/pdf-consignacion/<patente>')
@login_required
def generar_pdf_consignacion(patente):
    from fpdf import FPDF
    from flask import current_app
    import os
    
    vehiculo = Vehiculo.query.get_or_404(patente)
    
    if not vehiculo.propietario:
        flash('Este vehículo no tiene propietario registrado.', 'warning')
        return redirect(url_for('main.listar_vehiculos'))

    # Iniciamos el PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Reducimos los márgenes automáticos para asegurar que quepa en 1 hoja
    pdf.set_auto_page_break(auto=True, margin=10)

    # LOGO
    logo_path = os.path.join(current_app.static_folder, 'img', 'logo.png') 
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30) # Logo un poco más pequeño para no empujar el texto
    
    # TÍTULO (Centrado y ajustado al espacio del logo)
    pdf.set_y(15) 
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, 'CONTRATO DE CONSIGNACION DE VEHICULO', 0, 1, 'C')
    
    # Espacio extra después del título/logo
    pdf.ln(12)

    # I. IDENTIFICACIÓN
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'I. IDENTIFICACION', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"Nombre completo: {vehiculo.propietario.nombre} {vehiculo.propietario.apellido}", 0, 1)
    pdf.cell(0, 5, f"RUT: {vehiculo.propietario.rut_formateado()}", 0, 1)
    pdf.cell(0, 5, f"Direccion: {vehiculo.propietario.direccion}, {vehiculo.propietario.ciudad}", 0, 1)
    pdf.cell(0, 5, f"Numero de celular: {vehiculo.propietario.telefono}", 0, 1)
    pdf.ln(1)
    pdf.multi_cell(0, 5, "Declara ser dueno del vehiculo individualizado a continuacion:")
    pdf.ln(4)

    # II. IDENTIFICACIÓN DEL VEHÍCULO
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'II. IDENTIFICACION DEL VEHICULO', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"Marca: {vehiculo.marca}", 0, 1)
    pdf.cell(0, 5, f"Modelo: {vehiculo.modelo}", 0, 1)
    pdf.cell(0, 5, f"Ano: {vehiculo.ano}", 0, 1)
    pdf.cell(0, 5, f"Color: {vehiculo.color}", 0, 1)
    pdf.cell(0, 5, f"Patente: {vehiculo.patente}", 0, 1)
    pdf.cell(0, 5, f"Kilometraje: {vehiculo.kilometraje or 0} km", 0, 1)
    pdf.cell(0, 5, f"N Chasis (VIN): {vehiculo.chasis_n}", 0, 1)
    pdf.cell(0, 5, f"N Motor: {vehiculo.motor_n}", 0, 1)
    pdf.ln(4)

    # III. PRECIO SOLICITADO
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'III. PRECIO SOLICITADO', 0, 1)
    pdf.set_font('Arial', '', 10)
    precio_formateado = "${:,.0f}".format(vehiculo.precio_acordado or 0).replace(',', '.')
    pdf.cell(0, 6, f"Precio solicitado por el vehiculo: {precio_formateado}", 0, 1)
    pdf.multi_cell(0, 5, "Toda oferta recibida sera comunicada oportunamente para su evaluacion y aprobacion antes de concretar la venta.")
    pdf.ln(4)

    # IV. COMISIÓN
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'IV. COMISION DE LA AUTOMOTORA', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, "La comision por gestion de venta sera:\n\n"
                         "  o  $200.000 como comision minima, o\n"
                         "  o  El 3% del valor final de venta,\n\n"
                         "Aplicandose el monto que resulte mayor.\n\n"
                         "La comision sera descontada directamente del valor pagado por el comprador.")
    pdf.ln(4)

    # V. PAGO POR LAVADO Y MANTENCIÓN
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'V. PAGO POR LAVADO Y MANTENCION', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, "Se paga un monto unico de: $20.000\n"
                         "Por concepto de lavado inicial y mantencion diaria de limpieza. Monto no reembolsable.")
    
    # FIRMAS
    pdf.ln(6)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, "Firmas:", 0, 1)
    pdf.ln(12) # Espacio para que firmen a mano
    pdf.cell(90, 5, "___________________________________", 0, 0, 'C')
    pdf.cell(90, 5, "___________________________________", 0, 1, 'C')
    pdf.cell(90, 5, "PROPIETARIO", 0, 0, 'C')
    pdf.cell(90, 5, "AUTOMOTORA", 0, 1, 'C')

    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=consignacion_{vehiculo.patente}.pdf'
    return response


@bp.route('/vehiculos/historial/<patente>')
@login_required
def historial_vehiculo(patente):
    vehiculo = Vehiculo.query.get_or_404(patente)
    registros = vehiculo.registros.all() 
    
    # Capturamos de dónde viene (por defecto será 'vehiculos')
    origen = request.args.get('origen', 'vehiculos') 
    
    return render_template('historial_vehiculo.html', title=f'Historial: {vehiculo.patente}', vehiculo=vehiculo, registros=registros, origen=origen)