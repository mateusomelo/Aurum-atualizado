from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Importa a instância do db do módulo user
from .user import db

class Ticket(db.Model):
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='aberto')  # aberto, em_andamento, fechado
    priority = db.Column(db.String(50), nullable=False, default='media')  # baixa, media, alta, urgente
    service_type = db.Column(db.String(100), nullable=False)  # consultoria, seguranca, desenvolvimento
    
    # Relacionamentos simplificados
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos com backref
    user = db.relationship('User', foreign_keys=[user_id], backref='tickets')
    assigned_user = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tickets')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'service_type': self.service_type,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'assigned_to': self.assigned_to,
            'assigned_user_name': self.assigned_user.username if self.assigned_user else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }
