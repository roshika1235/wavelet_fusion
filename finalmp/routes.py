import os
import uuid
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import app, db
from models import User, FusionSession, UploadedImage
from fusion import process_fusion
import logging

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    fusion_sessions = FusionSession.query.filter_by(user_id=current_user.id).order_by(FusionSession.created_at.desc()).all()
    return render_template('dashboard.html', fusion_sessions=fusion_sessions)

@app.route('/fusion', methods=['GET', 'POST'])
@login_required
def fusion():
    if request.method == 'POST':
        session_name = request.form['session_name']
        num_images = int(request.form['num_images'])
        
        if not session_name:
            flash('Session name is required.', 'error')
            return render_template('fusion.html')
        
        if num_images < 2 or num_images > 10:
            flash('Number of images must be between 2 and 10.', 'error')
            return render_template('fusion.html')
        
        # Create fusion session
        fusion_session = FusionSession(
            user_id=current_user.id,
            session_name=session_name,
            num_images=num_images
        )
        db.session.add(fusion_session)
        db.session.commit()
        
        return redirect(url_for('upload_images', session_id=fusion_session.id))
    
    return render_template('fusion.html')

@app.route('/upload/<int:session_id>')
@login_required
def upload_images(session_id):
    fusion_session = FusionSession.query.get_or_404(session_id)
    
    # Check if user owns this session
    if fusion_session.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('upload.html', fusion_session=fusion_session)

@app.route('/upload_file/<int:session_id>', methods=['POST'])
@login_required
def upload_file(session_id):
    fusion_session = FusionSession.query.get_or_404(session_id)
    
    # Check if user owns this session
    if fusion_session.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Check if we already have enough images
        current_count = len(fusion_session.images)
        if current_count >= fusion_session.num_images:
            return jsonify({'error': 'Maximum number of images reached'}), 400
        
        # Generate unique filename
        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            file_size = os.path.getsize(filepath)
            
            # Save to database
            uploaded_image = UploadedImage(
                fusion_session_id=session_id,
                filename=filename,
                original_filename=file.filename,
                file_size=file_size
            )
            db.session.add(uploaded_image)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'filename': filename,
                'original_filename': file.filename,
                'current_count': current_count + 1,
                'total_needed': fusion_session.num_images
            })
        
        except Exception as e:
            logging.error(f"Error uploading file: {str(e)}")
            return jsonify({'error': 'Error uploading file'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/process_fusion/<int:session_id>', methods=['POST'])
@login_required
def process_fusion_route(session_id):
    fusion_session = FusionSession.query.get_or_404(session_id)
    
    # Check if user owns this session
    if fusion_session.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Check if we have enough images
    if len(fusion_session.images) != fusion_session.num_images:
        return jsonify({'error': 'Not enough images uploaded'}), 400
    
    try:
        # Update status to processing
        fusion_session.status = 'processing'
        db.session.commit()
        
        # Process fusion
        image_paths = [os.path.join(current_app.config['UPLOAD_FOLDER'], img.filename) 
                      for img in fusion_session.images]
        
        result_filename = f"fusion_{session_id}_{uuid.uuid4().hex}.png"
        result_path = os.path.join(current_app.config['RESULT_FOLDER'], result_filename)
        
        success = process_fusion(image_paths, result_path)
        
        if success:
            fusion_session.status = 'completed'
            fusion_session.result_filename = result_filename
            fusion_session.completed_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'result_url': url_for('view_result', session_id=session_id)
            })
        else:
            fusion_session.status = 'failed'
            db.session.commit()
            return jsonify({'error': 'Fusion processing failed'}), 500
    
    except Exception as e:
        logging.error(f"Error processing fusion: {str(e)}")
        fusion_session.status = 'failed'
        db.session.commit()
        return jsonify({'error': 'Error processing fusion'}), 500

@app.route('/result/<int:session_id>')
@login_required
def view_result(session_id):
    fusion_session = FusionSession.query.get_or_404(session_id)
    
    # Check if user owns this session
    if fusion_session.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    if fusion_session.status != 'completed':
        flash('Fusion not completed yet.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('result.html', fusion_session=fusion_session)

@app.route('/download/<int:session_id>')
@login_required
def download_result(session_id):
    fusion_session = FusionSession.query.get_or_404(session_id)
    
    # Check if user owns this session
    if fusion_session.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    if fusion_session.status != 'completed' or not fusion_session.result_filename:
        flash('No result available for download.', 'error')
        return redirect(url_for('dashboard'))
    
    result_path = os.path.join(current_app.config['RESULT_FOLDER'], fusion_session.result_filename)
    
    if not os.path.exists(result_path):
        flash('Result file not found.', 'error')
        return redirect(url_for('dashboard'))
    
    return send_file(result_path, as_attachment=True, 
                    download_name=f"{fusion_session.session_name}_fused.png")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/delete_session/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    fusion_session = FusionSession.query.get_or_404(session_id)
    
    # Check if user owns this session
    if fusion_session.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Delete uploaded files
        for image in fusion_session.images:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete result file
        if fusion_session.result_filename:
            result_path = os.path.join(current_app.config['RESULT_FOLDER'], fusion_session.result_filename)
            if os.path.exists(result_path):
                os.remove(result_path)
        
        # Delete from database
        db.session.delete(fusion_session)
        db.session.commit()
        
        flash('Session deleted successfully.', 'success')
    except Exception as e:
        logging.error(f"Error deleting session: {str(e)}")
        flash('Error deleting session.', 'error')
    
    return redirect(url_for('dashboard'))
