"""
Vehicle Image Rendering Service
Flask-based REST API for rendering vehicle SVGs with visual enhancements.
"""

import os
import io
import time
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template

from renderer import VehicleRenderer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max
app.config['RENDER_TIMEOUT'] = 30  # seconds
app.config['ALLOWED_EXTENSIONS'] = {'svg'}

# Initialize renderer
renderer = VehicleRenderer()


@app.route('/')
def index():
    """Serve the HTML test page."""
    return render_template('index.html')


@app.route('/render', methods=['POST'])
def render_vehicle():
    """
    Render endpoint - receives SVG, applies visual treatment, 
    adds watermark, scales, and returns PNG.
    
    Expected form fields:
    - vehicleSvg: The vehicle SVG file
    - watermarkSvg: The watermark SVG file (optional)
    - maxWidth: Maximum width in pixels (default: 800)
    - maxHeight: Maximum height in pixels (default: 600)
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    try:
        # Get parameters
        max_width = request.form.get('maxWidth', type=int, default=800)
        max_height = request.form.get('maxHeight', type=int, default=600)
        
        # Validate inputs
        if max_width < 1 or max_width > 4096:
            return jsonify({'error': 'maxWidth must be between 1 and 4096'}), 400
        if max_height < 1 or max_height > 4096:
            return jsonify({'error': 'maxHeight must be between 1 and 4096'}), 400
        
        # Get uploaded files
        vehicle_file = request.files.get('vehicleSvg')
        watermark_file = request.files.get('watermarkSvg')
        
        if not vehicle_file:
            return jsonify({'error': 'vehicleSvg is required'}), 400
        
        # Validate file types
        if vehicle_file.filename and not vehicle_file.filename.lower().endswith('.svg'):
            return jsonify({'error': 'vehicleSvg must be an SVG file'}), 400
        
        if watermark_file and watermark_file.filename and not watermark_file.filename.lower().endswith('.svg'):
            return jsonify({'error': 'watermarkSvg must be an SVG file'}), 400
        
        # Read SVG content
        vehicle_svg = vehicle_file.read().decode('utf-8')
        
        # Validate and sanitize SVG
        if len(vehicle_svg) > 1024 * 1024:  # 1MB limit
            return jsonify({'error': 'SVG file too large (max 1MB)'}), 400
        
        # Read watermark if provided
        watermark_svg = None
        if watermark_file:
            watermark_svg = watermark_file.read().decode('utf-8')
        
        # Render the image
        logger.info(f"[{request_id}] Starting render: maxWidth={max_width}, maxHeight={max_height}")
        
        result = renderer.render(
            vehicle_svg=vehicle_svg,
            watermark_svg=watermark_svg,
            max_width=max_width,
            max_height=max_height
        )
        
        # Calculate timing
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[{request_id}] Render completed in {elapsed_ms}ms")
        
        # Return PNG
        return send_file(
            io.BytesIO(result),
            mimetype='image/png',
            as_attachment=False,
            download_name=f'vehicle_{request_id}.png'
        )
        
    except ValueError as e:
        logger.warning(f"[{request_id}] Validation error: {e}")
        return jsonify({'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"[{request_id}] Render error: {e}", exc_info=True)
        return jsonify({'error': 'Internal rendering error'}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Run with reloader disabled for stability
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)