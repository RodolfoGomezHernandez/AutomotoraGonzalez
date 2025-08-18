from flask import render_template, request, flash, redirect, url_for, Blueprint, make_response, abort
from flask_login import login_required, current_user
from app import db
from sqlalchemy import or_, cast, String, Date
from sqlalchemy.exc import IntegrityError
from fpdf import FPDF
import os
import datetime

from .models import NotaVenta, Cliente, Vehiculo, Pago
from .forms import NotaVentaForm, ClienteForm, VehiculoForm

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return render_template('index.html', title='Inicio')

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

@bp.route('/notas-venta/crear', methods=['GET', 'POST'])
@login_required
def crear_nota_venta():
    form = NotaVentaForm()
    if form.validate_on_submit():
        try:
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

# ... (resto de rutas de notas de venta: editar, eliminar, pdf)

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
    query = Vehiculo.query
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(or_(
            Vehiculo.patente.like(search_term),
            Vehiculo.marca.like(search_term),
            Vehiculo.modelo.like(search_term)
        ))
    vehiculos = query.order_by(Vehiculo.marca).paginate(page=page, per_page=15)
    return render_template('listar_vehiculos.html', title='Listado de Vehículos', vehiculos=vehiculos, search_query=search_query)

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
        return redirect(url_for('main.listar_vehiculos'))
    return render_template('crear_editar_simple.html', title='Añadir Nuevo Vehículo', form=form)

@bp.route('/vehiculos/editar/<patente>', methods=['GET', 'POST'])
@login_required
def editar_vehiculo(patente):
    vehiculo = Vehiculo.query.get_or_404(patente)
    form = VehiculoForm(original_patente=vehiculo.patente, original_chasis_n=vehiculo.chasis_n, original_motor_n=vehiculo.motor_n, obj=vehiculo)
    if form.validate_on_submit():
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
