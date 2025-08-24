from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
from app.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.email import send_email

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    # Si ya existe al menos un usuario, no se permite registrar más.
    if User.query.first() is not None:
        flash('El registro de nuevos usuarios está deshabilitado.', 'warning')
        return redirect(url_for('auth.login'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('¡Felicidades! El usuario administrador ha sido creado.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Registro de Administrador', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Si no hay ningún usuario en la BD, redirige a la página de registro.
    if User.query.first() is None:
        flash('No hay usuarios registrados. Por favor, cree la cuenta de administrador.', 'info')
        return redirect(url_for('auth.register'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Email o contraseña inválidos.', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.index'))
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('auth.login'))
@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_password_token()
            send_email('Reseteo de Contraseña',
                       sender=current_app.config['ADMINS'][0],
                       recipients=[user.email],
                       text_body=render_template('email/reset_password.txt', user=user, token=token),
                       html_body=render_template('email/reset_password.html', user=user, token=token))
        flash('Se ha enviado un correo con las instrucciones para resetear tu contraseña.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title='Resetear Contraseña', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('El token es inválido o ha expirado.', 'warning')
        return redirect(url_for('auth.reset_password_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Tu contraseña ha sido reseteada exitosamente.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)