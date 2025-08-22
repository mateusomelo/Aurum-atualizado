from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.user import db

class Usuario(db.Model):
    __tablename__ = 'helpdesk_usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=False)  # administrador, tecnico, cliente
    empresa_id = db.Column(db.Integer, db.ForeignKey('helpdesk_empresas.id'), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    empresa = db.relationship('Empresa', backref='usuarios')
    chamados_criados = db.relationship('Chamado', foreign_keys='Chamado.usuario_id', backref='usuario')
    chamados_atendidos = db.relationship('Chamado', foreign_keys='Chamado.tecnico_id', backref='tecnico')
    
    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.nome}>'

class Empresa(db.Model):
    __tablename__ = 'helpdesk_empresas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(100), nullable=False)
    organizador = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    ativa = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    chamados = db.relationship('Chamado', backref='empresa', lazy=True)
    
    def __repr__(self):
        return f'<Empresa {self.nome_empresa}>'

class Servico(db.Model):
    __tablename__ = 'helpdesk_servicos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    chamados = db.relationship('Chamado', backref='servico', lazy=True)
    
    def __repr__(self):
        return f'<Servico {self.nome}>'

class Chamado(db.Model):
    __tablename__ = 'helpdesk_chamados'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='aberto')  # aberto, em_andamento, finalizado
    prioridade = db.Column(db.String(10), default='media')  # baixa, media, alta
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_finalizacao = db.Column(db.DateTime)
    
    # Chaves estrangeiras
    usuario_id = db.Column(db.Integer, db.ForeignKey('helpdesk_usuarios.id'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('helpdesk_empresas.id'), nullable=True)
    servico_id = db.Column(db.Integer, db.ForeignKey('helpdesk_servicos.id'), nullable=True)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('helpdesk_usuarios.id'), nullable=True)
    
    # Relacionamentos
    respostas = db.relationship('RespostaChamado', backref='chamado', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Chamado {self.titulo}>'

class RespostaChamado(db.Model):
    __tablename__ = 'helpdesk_respostas_chamados'
    
    id = db.Column(db.Integer, primary_key=True)
    resposta = db.Column(db.Text, nullable=False)
    data_resposta = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Chaves estrangeiras
    chamado_id = db.Column(db.Integer, db.ForeignKey('helpdesk_chamados.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('helpdesk_usuarios.id'), nullable=False)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='respostas')
    
    def __repr__(self):
        return f'<Resposta para Chamado {self.chamado_id}>'