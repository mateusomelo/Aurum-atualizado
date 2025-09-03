from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db # Importando o db do user.py

class TicketResponse(db.Model):
    __tablename__ = 'ticket_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)  # Para notas internas entre técnicos/admins
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    ticket = db.relationship('Ticket', backref='responses')
    user = db.relationship('User')
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'message': self.message,
            'is_internal': self.is_internal,
            'created_at': self.created_at.isoformat(),
            'user': self.user.username if self.user else None,
            'user_profile': self.user.profile if self.user else None
        }

