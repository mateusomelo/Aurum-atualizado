from datetime import datetime
from src.models.user import db
from src.utils.timezone_utils import get_brazil_time
import json

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=get_brazil_time, index=True)
    
    # Informações do usuário
    user_id = db.Column(db.Integer, db.ForeignKey('helpdesk_usuarios.id'), nullable=True)
    user_name = db.Column(db.String(100), nullable=True)  # Nome do usuário no momento da ação
    user_type = db.Column(db.String(20), nullable=True)   # administrador, tecnico, cliente
    user_email = db.Column(db.String(120), nullable=True)
    
    # Informações da sessão
    session_id = db.Column(db.String(100), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Suporte IPv4 e IPv6
    user_agent = db.Column(db.Text, nullable=True)
    
    # Informações da ação
    action = db.Column(db.String(100), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, VIEW
    module = db.Column(db.String(50), nullable=False, index=True)   # chamados, usuarios, empresas, auth, etc
    entity_type = db.Column(db.String(50), nullable=True)           # Chamado, Usuario, Empresa, etc
    entity_id = db.Column(db.Integer, nullable=True)                # ID da entidade afetada
    
    # Detalhes da ação
    description = db.Column(db.Text, nullable=False)               # Descrição da ação
    old_values = db.Column(db.Text, nullable=True)                 # JSON dos valores antigos
    new_values = db.Column(db.Text, nullable=True)                 # JSON dos valores novos
    
    # Informações do sistema
    endpoint = db.Column(db.String(200), nullable=True)            # Rota/endpoint acessado
    method = db.Column(db.String(10), nullable=True)               # GET, POST, PUT, DELETE
    status_code = db.Column(db.Integer, nullable=True)             # HTTP status code
    response_time = db.Column(db.Float, nullable=True)             # Tempo de resposta em ms
    
    # Metadados extras
    extra_data = db.Column(db.Text, nullable=True)                 # JSON com dados extras
    
    # Relacionamento
    usuario = db.relationship('Usuario', foreign_keys=[user_id], backref='activity_logs')
    
    def __init__(self, action, module, description, **kwargs):
        self.action = action.upper()
        self.module = module.lower()
        self.description = description
        
        # Definir outros campos opcionais
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def set_old_values(self, values_dict):
        """Converte dicionário de valores antigos para JSON"""
        if values_dict:
            self.old_values = json.dumps(values_dict, default=str, ensure_ascii=False)
    
    def set_new_values(self, values_dict):
        """Converte dicionário de valores novos para JSON"""
        if values_dict:
            self.new_values = json.dumps(values_dict, default=str, ensure_ascii=False)
    
    def set_extra_data(self, data_dict):
        """Converte dicionário de dados extras para JSON"""
        if data_dict:
            self.extra_data = json.dumps(data_dict, default=str, ensure_ascii=False)
    
    def get_old_values(self):
        """Retorna valores antigos como dicionário"""
        if self.old_values:
            try:
                return json.loads(self.old_values)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_new_values(self):
        """Retorna valores novos como dicionário"""
        if self.new_values:
            try:
                return json.loads(self.new_values)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_extra_data(self):
        """Retorna dados extras como dicionário"""
        if self.extra_data:
            try:
                return json.loads(self.extra_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_type': self.user_type,
            'user_email': self.user_email,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'action': self.action,
            'module': self.module,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'description': self.description,
            'old_values': self.get_old_values(),
            'new_values': self.get_new_values(),
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'response_time': self.response_time,
            'extra_data': self.get_extra_data()
        }
    
    def __repr__(self):
        return f'<ActivityLog {self.action} on {self.module} by {self.user_name or "System"}>'

# Índices adicionais para otimizar consultas
db.Index('idx_activity_log_user_action', ActivityLog.user_id, ActivityLog.action)
db.Index('idx_activity_log_module_timestamp', ActivityLog.module, ActivityLog.timestamp)
db.Index('idx_activity_log_entity', ActivityLog.entity_type, ActivityLog.entity_id)