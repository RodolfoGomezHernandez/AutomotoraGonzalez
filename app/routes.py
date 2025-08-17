from flask import render_template, request, flash, redirect, url_for, Blueprint, make_response, abort
from flask_login import login_required, current_user
from app import db
from sqlalchemy import or_, cast, String
from sqlalchemy.exc import IntegrityError
from fpdf import FPDF
import os
import datetime

from .models import NotaVenta, Cliente, Vehiculo, Pago
from .forms import NotaVentaForm
from .forms import ClienteForm, VehiculoForm

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return render_template('index.html', title='Inicio')

@bp.route('/notas-venta')
@login_required
def listar_notas_venta():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    # Nuevos parámetros de búsqueda
    search_field = request.args.get('search_field', 'todos')
    search_query = request.args.get('q', '', type=str)

    if per_page not in [20, 30, 50]:
        per_page = 20
    
    query = NotaVenta.query.join(Cliente).join(Vehiculo)

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
        else: # Búsqueda en todos los campos
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

    notas_venta = query.order_by(NotaVenta.fecha_venta.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template(
        'notas_venta/listar.html',
        title='Notas de Venta',
        notas=notas_venta,
        per_page=per_page,
        search_query=search_query,
        search_field=search_field
    )
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search_query = request.args.get('q', '', type=str)

    if per_page not in [20, 30, 50]:
        per_page = 20
    
    query = NotaVenta.query.join(Cliente).join(Vehiculo)

    if search_query:
        search_term = f"%{search_query}%"
        
        # Intentar convertir el término de búsqueda a fecha
        try:
            # Asumimos formato dd-mm-yyyy
            search_date = datetime.datetime.strptime(search_query, '%d-%m-%Y').date()
        except ValueError:
            search_date = None

        search_conditions = [
            cast(NotaVenta.id, String).like(search_term),
            Cliente.nombre.like(search_term),
            Cliente.apellido.like(search_term),
            Cliente.rut.like(search_term),
            Vehiculo.marca.like(search_term),
            Vehiculo.modelo.like(search_term),
            Vehiculo.patente.like(search_term),
            NotaVenta.estado.like(search_term)
        ]

        if search_date:
            search_conditions.append(cast(NotaVenta.fecha_venta, Date) == search_date)

        search_filter = or_(*search_conditions)
        query = query.filter(search_filter)

    notas_venta = query.order_by(NotaVenta.fecha_venta.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template(
        'notas_venta/listar.html',
        title='Notas de Venta',
        notas=notas_venta,
        per_page=per_page,
        search_query=search_query
    )




@bp.route('/notas-venta/crear', methods=['GET', 'POST'])
@login_required
def crear_nota_venta():
    form = NotaVentaForm()
    if form.validate_on_submit():
        try:
            # El pago se crea primero
            pago = Pago(
                metodo_pago=form.metodo_pago.data,
                total=form.monto_final.data
            )
            db.session.add(pago)
            db.session.flush() # Se usa flush para obtener el ID del pago antes del commit

            # Se crea la nota de venta
            nota = NotaVenta(
                cliente_rut=form.cliente_rut.data,
                vehiculo_patente=form.vehiculo_patente.data,
                user_id=current_user.id,
                pago_id=pago.id,
                fecha_venta=form.fecha_venta.data,
                monto_final=form.monto_final.data,
                estado=form.estado.data,
                observaciones=form.observaciones.data
            )
            db.session.add(nota)
            db.session.commit()
            flash('Nota de venta creada con éxito.', 'success')
            return redirect(url_for('main.listar_notas_venta'))
        except IntegrityError:
            db.session.rollback()
            flash('Error de integridad. Verifique que el cliente y el vehículo existan.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado: {e}', 'danger')

    return render_template('notas_venta/crear_editar.html', title='Crear Nota de Venta', form=form)

@bp.route('/notas-venta/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_nota_venta(id):
    nota = db.session.get(NotaVenta, id) or abort(404)
    form = NotaVentaForm(obj=nota)
    
    if form.validate_on_submit():
        try:
            nota.cliente_rut = form.cliente_rut.data
            nota.vehiculo_patente = form.vehiculo_patente.data
            nota.fecha_venta = form.fecha_venta.data
            nota.monto_final = form.monto_final.data
            nota.estado = form.estado.data
            nota.observaciones = form.observaciones.data
            
            if nota.pago:
                nota.pago.metodo_pago = form.metodo_pago.data
                nota.pago.total = form.monto_final.data

            db.session.commit()
            flash('Nota de venta actualizada con éxito.', 'success')
            return redirect(url_for('main.listar_notas_venta'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la nota de venta: {e}', 'danger')
    
    # Precargar datos en el formulario para la vista GET
    form.cliente_rut.data = nota.cliente_rut
    form.vehiculo_patente.data = nota.vehiculo_patente
    form.fecha_venta.data = nota.fecha_venta
    form.monto_final.data = nota.monto_final
    form.estado.data = nota.estado
    form.observaciones.data = nota.observaciones
    if nota.pago:
        form.metodo_pago.data = nota.pago.metodo_pago
            
    return render_template('notas_venta/crear_editar.html', title='Editar Nota de Venta', form=form, nota_id=id)

@bp.route('/notas-venta/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_nota_venta(id):
    nota = db.session.get(NotaVenta, id) or abort(404)
    try:
        # Es importante eliminar la nota primero, y el pago después si es necesario
        # por la relación de clave foránea. O configurar el borrado en cascada en el modelo.
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

# Clase personalizada para añadir cabecera y pie de página al PDF
class PDF(FPDF):
    def header(self):
        # Logo
        logo_path = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'app', 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 33)
        # Fuente Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Mover a la derecha
        self.cell(80)
        # Título
        self.cell(30, 10, 'Nota de Venta', 0, 0, 'C')
        # Salto de línea
        self.ln(20)

    def footer(self):
        # Posición a 1.5 cm del final
        self.set_y(-15)
        # Fuente Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Texto del pie de página
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
        self.cell(0, 10, 'Automotora Gonzalez | Gracias por su compra.', 0, 0, 'R')


@bp.route('/notas-venta/pdf/<int:id>')
@login_required
def generar_pdf(id):
    nota = db.session.get(NotaVenta, id) or abort(404)
    
    pdf = PDF()
    pdf.add_page()
    
    # --- Información General ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Folio: #{nota.id}", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Fecha de Venta: {nota.fecha_venta.strftime('%d-%m-%Y')}", 0, 1)
    pdf.ln(10)

    # --- Datos del Cliente y Vendedor ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(95, 10, 'Datos del Cliente', 1, 0, 'C')
    pdf.cell(95, 10, 'Datos del Vendedor', 1, 1, 'C')
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f"Nombre: {nota.cliente.nombre} {nota.cliente.apellido}", 1, 0)
    pdf.cell(95, 7, f"Nombre: {nota.vendedor.name}", 1, 1)
    pdf.cell(95, 7, f"RUT: {nota.cliente.rut}", 1, 0)
    pdf.cell(95, 7, f"Email: {nota.vendedor.email}", 1, 1)
    pdf.cell(95, 7, f"Telefono: {nota.cliente.telefono}", 1, 0)
    pdf.cell(95, 7, "", 1, 1) # Celda vacía para alinear
    
    # LÍNEA CORREGIDA: Se eliminó el último argumento '0' que causaba el error
    pdf.multi_cell(95, 7, f"Direccion: {nota.cliente.direccion}, {nota.cliente.ciudad}", 1)
    pdf.ln(10)

    # --- Detalles del Vehículo ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Detalles del Vehiculo', 1, 1, 'C')
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f"Patente: {nota.vehiculo.patente}", 1, 0)
    pdf.cell(95, 7, f"Marca / Modelo: {nota.vehiculo.marca} {nota.vehiculo.modelo}", 1, 1)
    pdf.cell(95, 7, f"Ano: {nota.vehiculo.ano}", 1, 0)
    pdf.cell(95, 7, f"N Chasis: {nota.vehiculo.chasis_n}", 1, 1)
    pdf.cell(95, 7, f"N Motor: {nota.vehiculo.motor_n}", 1, 0)
    pdf.cell(95, 7, "", 1, 1) # Celda vacía para alinear
    pdf.ln(10)

    # --- Condiciones de Pago y Total ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Condiciones de la Venta', 1, 1, 'C')

    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 7, f"Metodo de Pago: {nota.pago.metodo_pago.capitalize()}", 1, 1)
    pdf.multi_cell(0, 7, f"Observaciones: {nota.observaciones or 'Sin observaciones.'}", 1)
    
    pdf.set_font('Arial', 'B', 14)
    monto_formateado = "${:,.0f}".format(nota.monto_final).replace(',', '.')
    pdf.cell(0, 15, f"Monto Final: {monto_formateado}", 1, 1, 'R')

    # Generar la respuesta para el navegador
    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=nota_venta_{nota.id}.pdf'
    
    return response

@bp.route('/clientes/crear', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        cliente = Cliente(
            rut=form.rut.data,
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            telefono=form.telefono.data,
            direccion=form.direccion.data,
            ciudad=form.ciudad.data
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente añadido con éxito.', 'success')
        return redirect(url_for('main.index'))
    return render_template('crear_editar_simple.html', title='Añadir Nuevo Cliente', form=form)

@bp.route('/vehiculos/crear', methods=['GET', 'POST'])
@login_required
def crear_vehiculo():
    form = VehiculoForm()
    if form.validate_on_submit():
        vehiculo = Vehiculo(
            patente=form.patente.data,
            marca=form.marca.data,
            modelo=form.modelo.data,
            ano=form.ano.data,
            color=form.color.data,
            chasis_n=form.chasis_n.data,
            motor_n=form.motor_n.data,
            valor=form.valor.data,
            descripcion=form.descripcion.data
        )
        db.session.add(vehiculo)
        db.session.commit()
        flash('Vehículo añadido con éxito.', 'success')
        return redirect(url_for('main.index'))
    return render_template('crear_editar_simple.html', title='Añadir Nuevo Vehículo', form=form)

