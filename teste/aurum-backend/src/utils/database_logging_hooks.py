from sqlalchemy import event
from sqlalchemy.orm import object_session
from src.models.user import db
from src.utils.activity_logger import activity_logger
from flask import has_request_context
import json

class DatabaseLoggingHooks:
    """Hooks do SQLAlchemy para capturar todas as operações de banco automaticamente"""
    
    def __init__(self, app=None):
        self.app = app
        self.tracked_models = set()
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa os hooks com a aplicação Flask"""
        # Registrar eventos SQLAlchemy
        event.listen(db.session, 'before_commit', self.before_commit)
        event.listen(db.session, 'after_commit', self.after_commit)
        event.listen(db.session, 'after_rollback', self.after_rollback)
        
        # Registrar modelos para tracking
        self.register_tracked_models()
    
    def register_tracked_models(self):
        """Registra modelos que devem ser monitorados"""
        from src.models.helpdesk_models import Usuario, Empresa, Servico, Chamado, RespostaChamado
        from src.models.ticket import Ticket
        from src.models.ticket_response import TicketResponse
        from src.models.client import Client
        from src.models.service_type import ServiceType
        from src.models.user import User
        from src.models.contact import Contact
        
        # Modelos a serem monitorados (excluindo o log para evitar loops)
        tracked_models = [
            Usuario, Empresa, Servico, Chamado, RespostaChamado,
            Ticket, TicketResponse, Client, ServiceType, User, Contact
        ]
        
        for model in tracked_models:
            self.tracked_models.add(model)
            
            # Eventos por instância
            event.listen(model, 'before_insert', self.before_insert)
            event.listen(model, 'before_update', self.before_update) 
            event.listen(model, 'before_delete', self.before_delete)
    
    def should_log_model(self, instance):
        """Verifica se deve logar este modelo"""
        # Não logar o próprio ActivityLog para evitar loops infinitos
        if hasattr(instance, '__tablename__') and instance.__tablename__ == 'activity_logs':
            return False
        
        # Só logar se estiver em contexto de requisição
        if not has_request_context():
            return False
        
        # Verificar se o modelo está na lista de rastreamento
        return type(instance) in self.tracked_models
    
    def get_model_module(self, instance):
        """Determina o módulo baseado no modelo"""
        table_name = getattr(instance, '__tablename__', '')
        model_name = type(instance).__name__
        
        module_mapping = {
            'helpdesk_usuarios': 'usuarios',
            'helpdesk_empresas': 'empresas', 
            'helpdesk_servicos': 'servicos',
            'helpdesk_chamados': 'chamados',
            'helpdesk_respostas_chamados': 'chamados',
            'tickets': 'tickets',
            'ticket_responses': 'tickets',
            'user': 'usuarios',
            'clients': 'clientes',
            'service_types': 'servicos',
            'contacts': 'contatos'
        }
        
        return module_mapping.get(table_name, model_name.lower())
    
    def get_instance_dict(self, instance, exclude_fields=None):
        """Converte instância do modelo para dicionário seguro"""
        if exclude_fields is None:
            exclude_fields = ['senha_hash', 'password_hash', 'created_at', 'updated_at']
        
        result = {}
        
        try:
            # Usar inspect para obter atributos seguros
            from sqlalchemy.inspection import inspect
            mapper = inspect(type(instance))
            
            for column in mapper.columns:
                if column.name not in exclude_fields:
                    value = getattr(instance, column.name, None)
                    # Converter tipos não serializáveis
                    if hasattr(value, 'isoformat'):  # DateTime
                        result[column.name] = value.isoformat()
                    elif isinstance(value, (str, int, float, bool)) or value is None:
                        result[column.name] = value
                    else:
                        result[column.name] = str(value)
        
        except Exception as e:
            # Fallback seguro
            result = {'error': f'Could not serialize: {str(e)}'}
        
        return result
    
    def get_primary_key(self, instance):
        """Obtém a chave primária da instância"""
        try:
            from sqlalchemy.inspection import inspect
            mapper = inspect(type(instance))
            pk_columns = mapper.primary_key
            
            if len(pk_columns) == 1:
                return getattr(instance, pk_columns[0].name)
            else:
                # Chave composta
                return {col.name: getattr(instance, col.name) for col in pk_columns}
        except:
            return None
    
    def get_instance_name(self, instance):
        """Obtém um nome descritivo da instância"""
        # Tentar alguns campos comuns para nome
        name_fields = ['nome', 'name', 'title', 'titulo', 'email', 'nome_empresa']
        
        for field in name_fields:
            if hasattr(instance, field):
                value = getattr(instance, field)
                if value:
                    return str(value)
        
        # Fallback para chave primária
        pk = self.get_primary_key(instance)
        if pk:
            return f"ID {pk}"
        
        return "Unknown"
    
    def before_insert(self, mapper, connection, target):
        """Evento antes de inserir"""
        if not self.should_log_model(target):
            return
        
        # Armazenar dados para log após commit
        if not hasattr(target, '_log_data'):
            target._log_data = {}
        
        target._log_data['action'] = 'CREATE'
        target._log_data['new_values'] = self.get_instance_dict(target)
    
    def before_update(self, mapper, connection, target):
        """Evento antes de atualizar"""
        if not self.should_log_model(target):
            return
        
        # Capturar valores antigos
        if not hasattr(target, '_log_data'):
            target._log_data = {}
        
        target._log_data['action'] = 'UPDATE'
        target._log_data['old_values'] = {}
        target._log_data['new_values'] = {}
        
        # Obter valores antigos da sessão
        session = object_session(target)
        if session:
            old_instance = session.get(type(target), self.get_primary_key(target))
            if old_instance:
                target._log_data['old_values'] = self.get_instance_dict(old_instance)
        
        # Valores novos serão capturados no after_commit
        target._log_data['new_values'] = self.get_instance_dict(target)
    
    def before_delete(self, mapper, connection, target):
        """Evento antes de deletar"""
        if not self.should_log_model(target):
            return
        
        if not hasattr(target, '_log_data'):
            target._log_data = {}
        
        target._log_data['action'] = 'DELETE'
        target._log_data['old_values'] = self.get_instance_dict(target)
    
    def before_commit(self, session):
        """Evento antes do commit - prepara logs"""
        self.pending_logs = []
        
        # Iterar sobre objetos new, dirty e deleted
        for instance in session.new:
            if self.should_log_model(instance) and hasattr(instance, '_log_data'):
                self.prepare_log_entry(instance)
        
        for instance in session.dirty:
            if self.should_log_model(instance) and hasattr(instance, '_log_data'):
                self.prepare_log_entry(instance)
        
        for instance in session.deleted:
            if self.should_log_model(instance) and hasattr(instance, '_log_data'):
                self.prepare_log_entry(instance)
    
    def prepare_log_entry(self, instance):
        """Prepara entrada de log para ser salva após commit"""
        if not hasattr(instance, '_log_data'):
            return
        
        log_data = instance._log_data
        module = self.get_model_module(instance)
        entity_type = type(instance).__name__
        entity_id = self.get_primary_key(instance)
        instance_name = self.get_instance_name(instance)
        
        # Descrição baseada na ação
        action = log_data['action']
        if action == 'CREATE':
            description = f"Criou {entity_type} '{instance_name}'"
        elif action == 'UPDATE':
            description = f"Atualizou {entity_type} '{instance_name}'"
        elif action == 'DELETE':
            description = f"Deletou {entity_type} '{instance_name}'"
        else:
            description = f"{action} {entity_type} '{instance_name}'"
        
        # Preparar dados do log
        log_entry_data = {
            'action': action,
            'module': module,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'description': description,
            'old_values': log_data.get('old_values'),
            'new_values': log_data.get('new_values')
        }
        
        self.pending_logs.append(log_entry_data)
    
    def after_commit(self, session):
        """Evento após commit bem-sucedido - salva logs"""
        if not hasattr(self, 'pending_logs'):
            return
        
        # Salvar todos os logs preparados
        for log_data in self.pending_logs:
            try:
                activity_logger.log_activity(**log_data)
            except Exception as e:
                print(f"Erro ao salvar log automático: {e}")
        
        # Limpar logs pendentes
        self.pending_logs = []
    
    def after_rollback(self, session):
        """Evento após rollback - limpa logs pendentes"""
        if hasattr(self, 'pending_logs'):
            self.pending_logs = []

# Instância global dos hooks
database_logging_hooks = DatabaseLoggingHooks()