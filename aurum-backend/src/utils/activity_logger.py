from flask import request, session, g
from src.models.activity_log import ActivityLog
from src.models.user import db
from src.models.helpdesk_models import Usuario
import time
import functools
import traceback
from src.utils.debug_logging import debug_session_info, debug_log_attempt, debug_print

class ActivityLogger:
    """Sistema centralizado de logging de atividades"""
    
    def __init__(self):
        self.start_time = None
    
    def get_user_info(self):
        """Obtém informações do usuário atual"""
        user_info = {
            'user_id': None,
            'user_name': None,
            'user_type': None,
            'user_email': None,
            'session_id': None
        }
        
        try:
            # Informações da sessão
            user_info['session_id'] = session.get('session_id', str(session.sid) if hasattr(session, 'sid') else None)
            
            # Sistema helpdesk
            if 'user_id' in session:
                user_info['user_id'] = session['user_id']
                user_info['user_name'] = session.get('user_name')
                user_info['user_type'] = session.get('user_type')
                user_info['user_email'] = session.get('user_email')
                
                # Se não temos nome na sessão, buscar no banco
                if not user_info['user_name'] and user_info['user_id']:
                    user = Usuario.query.get(user_info['user_id'])
                    if user:
                        user_info['user_name'] = user.nome
                        user_info['user_email'] = user.email
                        user_info['user_type'] = user.tipo_usuario
        
        except Exception as e:
            print(f"Erro ao obter informações do usuário para log: {e}")
        
        return user_info
    
    def get_request_info(self):
        """Obtém informações da requisição atual"""
        request_info = {
            'ip_address': None,
            'user_agent': None,
            'endpoint': None,
            'method': None
        }
        
        try:
            if request:
                # IP do cliente (considerando proxies)
                request_info['ip_address'] = request.environ.get('HTTP_X_REAL_IP', 
                                                               request.environ.get('HTTP_X_FORWARDED_FOR', 
                                                                                  request.remote_addr))
                
                # User Agent
                request_info['user_agent'] = request.headers.get('User-Agent', '')[:500]  # Limitar tamanho
                
                # Endpoint e método
                request_info['endpoint'] = request.endpoint or request.path
                request_info['method'] = request.method
                
        except Exception as e:
            print(f"Erro ao obter informações da requisição para log: {e}")
        
        return request_info
    
    def log_activity(self, action, module, description, **kwargs):
        """
        Registra uma atividade no log
        
        Args:
            action: Tipo da ação (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, VIEW, etc)
            module: Módulo do sistema (chamados, usuarios, empresas, auth, etc)
            description: Descrição da ação
            **kwargs: Campos adicionais (entity_type, entity_id, old_values, new_values, etc)
        """
        try:
            # Debug da tentativa de log
            debug_log_attempt(action, module, description)
            # Obter informações do usuário e requisição
            user_info = self.get_user_info()
            request_info = self.get_request_info()
            
            # Calcular tempo de resposta se disponível
            response_time = None
            if hasattr(g, 'start_time'):
                response_time = round((time.time() - g.start_time) * 1000, 2)  # em ms
            
            # Criar registro de log
            log_entry = ActivityLog(
                action=action,
                module=module,
                description=description,
                **user_info,
                **request_info,
                response_time=response_time,
                **kwargs
            )
            
            # Processar valores antigos e novos se fornecidos
            if 'old_values' in kwargs:
                log_entry.set_old_values(kwargs['old_values'])
            if 'new_values' in kwargs:
                log_entry.set_new_values(kwargs['new_values'])
            if 'extra_data' in kwargs:
                log_entry.set_extra_data(kwargs['extra_data'])
            
            # Salvar no banco
            db.session.add(log_entry)
            db.session.commit()
            
            debug_print(f"✅ Log salvo com sucesso - ID: {log_entry.id}")
            return log_entry
            
        except Exception as e:
            print(f"Erro ao registrar log de atividade: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # Fazer rollback para não afetar outras operações
            try:
                db.session.rollback()
            except:
                pass
            return None
    
    def log_login(self, user_id, user_name, user_type, success=True, reason=None):
        """Log específico para login"""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        description = f"Login realizado com sucesso para {user_name}" if success else f"Falha no login: {reason}"
        
        extra_data = {}
        if not success and reason:
            extra_data['failure_reason'] = reason
        
        return self.log_activity(
            action=action,
            module="auth",
            description=description,
            user_id=user_id if success else None,
            user_name=user_name,
            user_type=user_type if success else None,
            extra_data=extra_data if extra_data else None
        )
    
    def log_logout(self, user_id, user_name):
        """Log específico para logout"""
        return self.log_activity(
            action="LOGOUT",
            module="auth", 
            description=f"Logout realizado por {user_name}",
            user_id=user_id,
            user_name=user_name
        )
    
    def log_create(self, module, entity_type, entity_id, description, new_values=None):
        """Log para criação de entidades"""
        return self.log_activity(
            action="CREATE",
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            new_values=new_values
        )
    
    def log_update(self, module, entity_type, entity_id, description, old_values=None, new_values=None):
        """Log para atualização de entidades"""
        return self.log_activity(
            action="UPDATE",
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            old_values=old_values,
            new_values=new_values
        )
    
    def log_delete(self, module, entity_type, entity_id, description, old_values=None):
        """Log para exclusão de entidades"""
        return self.log_activity(
            action="DELETE",
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            old_values=old_values
        )
    
    def log_view(self, module, entity_type=None, entity_id=None, description=None):
        """Log para visualização/acesso"""
        if not description:
            description = f"Acessou {module}"
            if entity_type and entity_id:
                description += f" - {entity_type} ID {entity_id}"
        
        return self.log_activity(
            action="VIEW",
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description
        )

# Instância global do logger
activity_logger = ActivityLogger()

def log_activity(action, module, description, **kwargs):
    """Função de conveniência para logging"""
    return activity_logger.log_activity(action, module, description, **kwargs)

def log_endpoint_access(func):
    """Decorator para logar acesso a endpoints automaticamente"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Marcar tempo de início
        g.start_time = time.time()
        
        try:
            # Executar função
            result = func(*args, **kwargs)
            
            # Log de acesso bem-sucedido
            activity_logger.log_view(
                module=request.endpoint.split('.')[0] if request.endpoint else 'unknown',
                description=f"Acessou endpoint {request.endpoint or request.path}"
            )
            
            return result
            
        except Exception as e:
            # Log de erro
            activity_logger.log_activity(
                action="ERROR",
                module=request.endpoint.split('.')[0] if request.endpoint else 'unknown',
                description=f"Erro ao acessar {request.endpoint or request.path}: {str(e)}",
                extra_data={'error': str(e), 'traceback': traceback.format_exc()}
            )
            raise
    
    return wrapper