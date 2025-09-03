from flask import request, session, g, has_request_context
from src.utils.activity_logger import activity_logger
import time
import json

class GlobalLoggingMiddleware:
    """Middleware global para capturar todas as atividades do site"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa o middleware com a aplicação Flask"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_request(self.teardown_request)
    
    def before_request(self):
        """Executado antes de cada requisição"""
        g.start_time = time.time()
        g.should_log = True
        
        # Filtrar requisições que não devem ser logadas
        if self.should_skip_logging():
            g.should_log = False
            return
        
        # Log básico de acesso
        self.log_request_access()
    
    def after_request(self, response):
        """Executado após cada requisição"""
        if not getattr(g, 'should_log', True):
            return response
        
        # Calcular tempo de resposta
        response_time = None
        if hasattr(g, 'start_time'):
            response_time = round((time.time() - g.start_time) * 1000, 2)
        
        # Log detalhado da resposta
        self.log_response_details(response, response_time)
        
        return response
    
    def teardown_request(self, exception=None):
        """Executado no final de cada requisição (com ou sem erro)"""
        if exception and getattr(g, 'should_log', True):
            self.log_request_error(exception)
    
    def should_skip_logging(self):
        """Determina se deve pular o log desta requisição"""
        if not has_request_context():
            return True
        
        # Pular arquivos estáticos
        if request.endpoint == 'static' or (request.path and any(
            request.path.endswith(ext) for ext in ['.css', '.js', '.ico', '.png', '.jpg', '.gif', '.svg', '.woff', '.woff2', '.ttf']
        )):
            return True
        
        # Pular alguns endpoints internos
        skip_endpoints = [
            'activity_logs.logs_api',  # API de logs (evitar loop)
            'debughelper'
        ]
        
        if request.endpoint in skip_endpoints:
            return True
        
        return False
    
    def log_request_access(self):
        """Log de acesso à requisição"""
        try:
            # Determinar módulo baseado na URL
            module = self.determine_module()
            
            # Descrição da ação
            description = f"Acessou {request.method} {request.path}"
            if request.endpoint:
                description = f"Acessou endpoint '{request.endpoint}'"
            
            # Dados extras da requisição
            extra_data = {
                'path': request.path,
                'query_string': request.query_string.decode('utf-8') if request.query_string else None,
                'referrer': request.referrer,
                'content_length': request.content_length
            }
            
            # Se tem dados POST/PUT, capturar (sem senhas)
            if request.method in ['POST', 'PUT', 'PATCH'] and request.is_json:
                try:
                    json_data = request.get_json()
                    if json_data:
                        # Remover campos sensíveis
                        safe_data = self.sanitize_request_data(json_data)
                        extra_data['request_data'] = safe_data
                except:
                    pass
            elif request.method in ['POST', 'PUT', 'PATCH'] and request.form:
                # Dados de formulário
                form_data = dict(request.form)
                safe_form_data = self.sanitize_request_data(form_data)
                extra_data['form_data'] = safe_form_data
            
            activity_logger.log_activity(
                action="ACCESS",
                module=module,
                description=description,
                method=request.method,
                endpoint=request.endpoint or request.path,
                extra_data=extra_data
            )
            
        except Exception as e:
            # Não falhar a requisição por erro de log
            print(f"Erro no log de acesso: {e}")
    
    def log_response_details(self, response, response_time):
        """Log detalhado da resposta"""
        try:
            # Só logar se teve alguma atividade significativa
            if response.status_code >= 400 or request.method != 'GET':
                module = self.determine_module()
                
                # Determinar tipo de ação baseado no método e status
                action = self.determine_action_type(response.status_code)
                
                description = f"{request.method} {request.path} - Status {response.status_code}"
                
                extra_data = {
                    'response_size': len(response.get_data()) if hasattr(response, 'get_data') else None,
                    'content_type': response.content_type
                }
                
                activity_logger.log_activity(
                    action=action,
                    module=module,
                    description=description,
                    status_code=response.status_code,
                    response_time=response_time,
                    method=request.method,
                    endpoint=request.endpoint or request.path,
                    extra_data=extra_data
                )
        
        except Exception as e:
            print(f"Erro no log de resposta: {e}")
    
    def log_request_error(self, exception):
        """Log de erro na requisição"""
        try:
            import traceback
            
            module = self.determine_module()
            
            description = f"Erro em {request.method} {request.path}: {str(exception)}"
            
            extra_data = {
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'traceback': traceback.format_exc(),
                'path': request.path,
                'method': request.method
            }
            
            activity_logger.log_activity(
                action="ERROR",
                module=module,
                description=description,
                status_code=500,
                method=request.method,
                endpoint=request.endpoint or request.path,
                extra_data=extra_data
            )
        
        except Exception as e:
            print(f"Erro no log de exceção: {e}")
    
    def determine_module(self):
        """Determina o módulo baseado na URL/endpoint"""
        if not request.path:
            return "system"
        
        path = request.path.lower()
        
        # Mapeamento de URLs para módulos
        if '/helpdesk' in path or request.endpoint and 'helpdesk' in request.endpoint:
            if '/chamado' in path:
                return "chamados"
            elif '/usuario' in path or '/login' in path or '/logout' in path:
                return "usuarios"
            elif '/empresa' in path:
                return "empresas"
            elif '/servico' in path:
                return "servicos"
            elif '/relatorio' in path:
                return "relatorios"
            elif '/notificacao' in path:
                return "notificacoes"
            else:
                return "helpdesk"
        
        elif '/api' in path:
            if '/tickets' in path:
                return "tickets"
            elif '/users' in path or '/auth' in path:
                return "usuarios"
            elif '/clients' in path:
                return "clientes"
            elif '/contact' in path:
                return "contato"
            else:
                return "api"
        
        elif '/logs' in path:
            return "logs"
        
        elif '/static' in path:
            return "static"
        
        else:
            return "system"
    
    def determine_action_type(self, status_code):
        """Determina o tipo de ação baseado no método HTTP e status"""
        if status_code >= 500:
            return "ERROR"
        elif status_code >= 400:
            return "ERROR"  # Cliente error também é um erro
        elif request.method == 'POST':
            return "CREATE"
        elif request.method in ['PUT', 'PATCH']:
            return "UPDATE"
        elif request.method == 'DELETE':
            return "DELETE"
        else:
            return "VIEW"
    
    def sanitize_request_data(self, data):
        """Remove dados sensíveis dos logs"""
        if not isinstance(data, dict):
            return data
        
        sensitive_fields = [
            'password', 'senha', 'pwd', 'pass',
            'secret', 'token', 'key', 'auth',
            'credit_card', 'ssn', 'cpf', 'cnpj'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = "***HIDDEN***"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_request_data(value)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize_request_data(item) if isinstance(item, dict) else item for item in value]
            else:
                # Limitar tamanho de strings muito grandes
                if isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + "...[TRUNCATED]"
                else:
                    sanitized[key] = value
        
        return sanitized

# Instância global do middleware
global_logging_middleware = GlobalLoggingMiddleware()