from flask import Blueprint, jsonify, session, request
from src.utils.debug_logging import debug_session_info, toggle_debug, debug_print
from src.utils.activity_logger import activity_logger
from src.models.activity_log import ActivityLog
from src.models.helpdesk_models import Usuario
from src.models.user import db
import json

debug_logs_bp = Blueprint('debug_logs', __name__)

@debug_logs_bp.route('/debug/session')
def debug_session():
    """Endpoint para debugar informações da sessão"""
    debug_session_info()
    
    return jsonify({
        'session_keys': list(session.keys()),
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'user_type': session.get('user_type'),
        'user_email': session.get('user_email'),
        'has_request_context': True,
        'path': request.path,
        'method': request.method
    })

@debug_logs_bp.route('/debug/test-log')
def test_log():
    """Endpoint para testar criação de log manualmente"""
    try:
        debug_print("🧪 Testando criação de log manual...")
        
        log_entry = activity_logger.log_activity(
            action="TEST",
            module="debug", 
            description="Log de teste manual",
            extra_data={'test': True, 'timestamp': str(db.func.now())}
        )
        
        return jsonify({
            'success': True,
            'log_id': log_entry.id if log_entry else None,
            'message': 'Log de teste criado com sucesso!'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debug_logs_bp.route('/debug/recent-logs')
def recent_logs():
    """Mostra os últimos 10 logs para debug"""
    try:
        logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
        
        result = []
        for log in logs:
            result.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'action': log.action,
                'module': log.module,
                'description': log.description,
                'user_name': log.user_name,
                'user_type': log.user_type,
                'user_id': log.user_id
            })
        
        return jsonify({
            'total_logs': ActivityLog.query.count(),
            'recent_logs': result
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debug_logs_bp.route('/debug/toggle-debug')
def toggle_debug_mode():
    """Liga/desliga modo debug"""
    toggle_debug()
    return jsonify({'message': 'Debug mode toggled'})

@debug_logs_bp.route('/debug/users')
def debug_users():
    """Lista usuários para debug"""
    try:
        users = Usuario.query.all()
        result = []
        
        for user in users:
            result.append({
                'id': user.id,
                'nome': user.nome,
                'email': user.email,
                'tipo_usuario': user.tipo_usuario,
                'ativo': user.ativo
            })
        
        return jsonify({
            'total_users': len(users),
            'users': result,
            'current_session_user_id': session.get('user_id')
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debug_logs_bp.route('/debug/force-login-log')
def force_login_log():
    """Força criação de log de login para teste"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Usuário não logado'}), 400
        
        user = Usuario.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        debug_print("🔧 Forçando criação de log de login...")
        
        log_entry = activity_logger.log_login(
            user_id=user.id,
            user_name=user.nome,
            user_type=user.tipo_usuario,
            success=True
        )
        
        return jsonify({
            'success': True,
            'log_id': log_entry.id if log_entry else None,
            'user_name': user.nome,
            'message': 'Log de login forçado criado!'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debug_logs_bp.route('/debug/log-batch', methods=['POST'])
def receive_log_batch():
    """Recebe logs em lote do JavaScript frontend"""
    try:
        data = request.get_json()
        if not data or 'logs' not in data:
            return jsonify({'error': 'Dados inválidos'}), 400
        
        logs = data['logs']
        processed = 0
        
        for log_data in logs:
            try:
                # Processar cada log individual
                activity_logger.log_activity(
                    action=log_data.get('action', 'UNKNOWN'),
                    module=log_data.get('module', 'frontend'),
                    description=log_data.get('description', 'Ação do frontend'),
                    extra_data={
                        'frontend_timestamp': log_data.get('timestamp'),
                        'page_url': log_data.get('page_url'),
                        'page_title': log_data.get('page_title'),
                        'user_agent': log_data.get('user_agent'),
                        'screen_resolution': log_data.get('screen_resolution'),
                        'viewport_size': log_data.get('viewport_size'),
                        'frontend_data': log_data.get('extra_data', {})
                    }
                )
                processed += 1
                
            except Exception as e:
                print(f"Erro ao processar log individual: {e}")
                continue
        
        return jsonify({
            'success': True,
            'processed': processed,
            'total': len(logs),
            'message': f'{processed}/{len(logs)} logs processados com sucesso'
        })
        
    except Exception as e:
        import traceback
        print(f"Erro ao processar batch de logs: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500