from flask import Flask, jsonify
from config.config import Config
from extensions import db, jwt
from routes.auth import auth_bp
from routes.users import users_bp
from routes.ai import ai_bp
from routes.rag import rag_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(rag_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Route not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    @jwt.unauthorized_loader
    def unauthorized(e):
        return jsonify({'error': 'Missing or invalid token'}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_data):
        return jsonify({'error': 'Token has expired'}), 401

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
