from flask import session, request, has_request_context
from src.models.helpdesk_models import Usuario
import traceback

def debug_session_info():
    """Função de debug para verificar informações da sessão"""
    if not has_request_context():
        print("🚫 DEBUG: Não há contexto de request")
        return
    
    print("\n" + "="*50)
    print("🔍 DEBUG: Informações da Sessão")
    print("="*50)
    
    # Verificar sessão Flask
    print(f"📝 Session keys: {list(session.keys())}")
    print(f"👤 user_id na sessão: {session.get('user_id', 'NÃO ENCONTRADO')}")
    print(f"📧 user_name na sessão: {session.get('user_name', 'NÃO ENCONTRADO')}")
    print(f"🎭 user_type na sessão: {session.get('user_type', 'NÃO ENCONTRADO')}")
    print(f"📩 user_email na sessão: {session.get('user_email', 'NÃO ENCONTRADO')}")
    
    # Verificar request
    if request:
        print(f"🌐 Path: {request.path}")
        print(f"🔧 Method: {request.method}")
        print(f"🎯 Endpoint: {request.endpoint}")
        print(f"🌍 IP: {request.remote_addr}")
    
    # Tentar buscar usuário no banco se temos ID
    user_id = session.get('user_id')
    if user_id:
        try:
            user = Usuario.query.get(user_id)
            if user:
                print(f"✅ Usuário encontrado no banco:")
                print(f"   - Nome: {user.nome}")
                print(f"   - Email: {user.email}")
                print(f"   - Tipo: {user.tipo_usuario}")
                print(f"   - Ativo: {user.ativo}")
            else:
                print(f"❌ Usuário ID {user_id} NÃO encontrado no banco")
        except Exception as e:
            print(f"🚨 Erro ao buscar usuário no banco: {e}")
            print(f"📋 Traceback: {traceback.format_exc()}")
    else:
        print("❌ Nenhum user_id na sessão")
    
    print("="*50 + "\n")

def debug_log_attempt(action, module, description):
    """Debug de tentativa de log"""
    print(f"\n🎯 DEBUG: Tentando logar - {action} em {module}: {description}")
    debug_session_info()

# Função para ativar/desativar debug
DEBUG_ENABLED = True

def toggle_debug():
    global DEBUG_ENABLED
    DEBUG_ENABLED = not DEBUG_ENABLED
    print(f"🔧 Debug de logs {'ATIVADO' if DEBUG_ENABLED else 'DESATIVADO'}")

def debug_print(message):
    if DEBUG_ENABLED:
        print(f"🐛 DEBUG: {message}")