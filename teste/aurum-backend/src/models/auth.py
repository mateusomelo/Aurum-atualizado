from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    profile = db.Column(db.String(20), nullable=False)  # 'administrador', 'tecnico', 'usuario'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Hash e armazena a senha"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verifica se a senha está correta"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'profile': self.profile,
            'created_at': self.created_at.isoformat()
        }

class Ticket(db.Model):
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'), nullable=True)
    status = db.Column(db.String(20), default='aberto')  # 'aberto', 'em_andamento', 'fechado'
    priority = db.Column(db.String(10), default='media')  # 'baixa', 'media', 'alta'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], backref='tickets')
    assigned_user = db.relationship('User', foreign_keys=[assigned_to])
    
    def to_dict(self):
        from .client import Client
        from .service_type import ServiceType
        
        client = Client.query.get(self.client_id) if self.client_id else None
        service_type = ServiceType.query.get(self.service_type_id) if self.service_type_id else None
        
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'service_type_id': self.service_type_id,
            'service_type': service_type.name if service_type else None,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'client_id': self.client_id,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user': self.user.username if self.user else None,
            'assigned_user': self.assigned_user.username if self.assigned_user else None,
            'client': client.name if client else None
        }

