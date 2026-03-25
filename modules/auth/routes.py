from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, logout_user, login_required


from datetime import datetime
from itsdangerous import URLSafeTimedSerializer

#local imports
from core.database import db
from modules.auth.models import User
from modules.auth.forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, UpdateProfileForm, ChangePasswordForm
from core.config import Config# Import app to get secret key
from core import csrf
from core.utils import send_email

config = Config()
auth_bp = Blueprint('auth', __name__,template_folder='templates')

s = URLSafeTimedSerializer(config.SECRET_KEY)



@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            student_number=form.student_number.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        token = s.dumps(user.email, salt='email-confirm-salt')
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        html = render_template('auth/email/confirm_email.html', confirm_url=confirm_url, user=user)
        subject = "Please confirm your email"
        send_email(user.email, subject, html)

        flash('Your account has been created! Please check your email to confirm your account.', 'success')
        return redirect(url_for('auth.login'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')

    return render_template('auth/register.html', form=form)

@auth_bp.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm-salt', max_age=3600)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if user.email_confirmed:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.email_confirmed = True
        user.email_confirmed_on = datetime.now()
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.email_confirmed:
                flash('Please confirm your email address first.', 'warning')
                return redirect(url_for('auth.login'))

            if user.is_active:
                login_user(user, remember=form.remember.data)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
            else:
                flash('Your account has been deactivated. Please contact administrator.', 'warning')
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = s.dumps(user.email, salt='password-reset-salt')
            # Here you would send the email with the reset link
            # For now, we'll just flash the token
            flash(f'A password reset link has been sent to your email. Token: {token}', 'info')
        else:
            flash('Email not found.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            flash('Your password has been updated! You are now able to log in.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form, token=token)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_form = UpdateProfileForm()
    password_form = ChangePasswordForm()

    if profile_form.submit_profile.data and profile_form.validate_on_submit():
        current_user.first_name = profile_form.first_name.data
        current_user.last_name = profile_form.last_name.data
        current_user.phone = profile_form.phone.data
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('auth.profile'))

    if password_form.submit_password.data and password_form.validate_on_submit():
        if current_user.check_password(password_form.current_password.data):
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash('Your password has been changed.', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Incorrect current password.', 'danger')

    profile_form.first_name.data = current_user.first_name
    profile_form.last_name.data = current_user.last_name
    profile_form.phone.data = current_user.phone
    
    return render_template('auth/profile.html', profile_form=profile_form, password_form=password_form)

@auth_bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user = current_user
    db.session.delete(user)
    db.session.commit()
    logout_user()
    flash('Your account has been permanently deleted.', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/resend_confirmation', methods=['GET', 'POST'])
def resend_confirmation():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if user.email_confirmed:
                flash('Your account has already been confirmed.', 'success')
            else:
                token = s.dumps(user.email, salt='email-confirm-salt')
                confirm_url = url_for('auth.confirm_email', token=token, _external=True)
                html = render_template('auth/email/confirm_email.html', confirm_url=confirm_url, user=user)
                subject = "Please confirm your email"
                send_email(user.email, subject, html)
                flash('A new confirmation email has been sent.', 'info')
        else:
            flash('Email not found.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/resend_confirmation.html', form=form)


@auth_bp.route('/privacy')
def privacy():
    return render_template('privacy_policy.html')
