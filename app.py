from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import os
from markitdown import MarkItDown
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "xlsx", "txt", "html", "csv", "json", "xml"}

for folder in [UPLOAD_FOLDER, RESULT_FOLDER, 'logs']:
    os.makedirs(folder, exist_ok=True)

logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler('logs/app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
app.logger.addHandler(handler)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    for folder in [UPLOAD_FOLDER, RESULT_FOLDER]:
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                    app.logger.info(f"Cleaned up file: {filepath}")
                except Exception as e:
                    app.logger.error(f"Error cleaning up {filepath}: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html', 
                         allowed_extensions=ALLOWED_EXTENSIONS,
                         max_size_mb=app.config['MAX_CONTENT_LENGTH']/(1024*1024))

@app.route('/upload', methods=['POST'])
def upload():
    cleanup_old_files()
    
    try:
        if 'file' not in request.files:
            flash("No se seleccionó ningún archivo", "error")
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash("No se seleccionó ningún archivo", "error")
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash(f"Tipo de archivo no permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}", "error")
            return redirect(url_for('index'))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"{timestamp}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(filepath)
        app.logger.info(f"File uploaded: {filepath}")
        
        md = MarkItDown()
        result = md.convert(filepath)
        
        md_filename = f"{os.path.splitext(filename)[0]}.md"
        md_filepath = os.path.join(RESULT_FOLDER, md_filename)
        
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(result.text_content)
        
        app.logger.info(f"Conversion successful: {md_filepath}")
        flash("¡Conversión exitosa!", "success")
        
        return send_file(
            md_filepath,
            as_attachment=True,
            download_name=md_filename
        )
        
    except FileNotFoundError:
        flash("El archivo no se encontró en el servidor. Por favor, inténtalo de nuevo.", "error")
    except PermissionError:
        flash("No tienes permisos para acceder a este archivo. Contacta al administrador.", "error")
    except Exception as e:
        app.logger.error(f"Error durante la conversión: {str(e)}")
        flash(f"Ocurrió un error inesperado: {str(e)}", "error")
    return redirect(url_for('index'))

@app.errorhandler(413)
def request_entity_too_large(error):
    flash(f"El archivo excede el tamaño máximo permitido de {app.config['MAX_CONTENT_LENGTH']/(1024*1024)}MB", "error")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)