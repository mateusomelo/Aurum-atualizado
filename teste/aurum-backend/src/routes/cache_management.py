from flask import Blueprint, jsonify, request, session, flash, redirect, url_for, render_template
from src.utils.cache_cleaner import CacheCleaner
from src.utils import admin_required, login_required
import logging

cache_bp = Blueprint('cache_management', __name__)
logger = logging.getLogger(__name__)

# Instância global do cache cleaner (será inicializada no main.py)
cache_cleaner = None

def init_cache_cleaner(app):
    """Inicializa o cache cleaner com a aplicação Flask"""
    global cache_cleaner
    cache_cleaner = CacheCleaner(app)
    return cache_cleaner

@cache_bp.route('/api/cache/cleanup', methods=['POST'])
@login_required
def manual_cleanup():
    """Endpoint para limpeza manual do cache"""
    try:
        if not cache_cleaner:
            return jsonify({'error': 'Cache cleaner não inicializado'}), 500
        
        # Verificar se usuário é admin
        if session.get('user_type') != 'administrador':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        
        results = cache_cleaner.run_full_cleanup()
        return jsonify({
            'success': True,
            'message': 'Limpeza executada com sucesso',
            'results': results
        })
    except Exception as e:
        logger.error(f"Erro na limpeza manual: {e}")
        return jsonify({'error': str(e)}), 500

@cache_bp.route('/api/cache/status', methods=['GET'])
@login_required
def get_cache_status():
    """Retorna status atual do cache e sistema"""
    try:
        if not cache_cleaner:
            return jsonify({'error': 'Cache cleaner não inicializado'}), 500
        
        # Verificar se usuário é admin
        if session.get('user_type') != 'administrador':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        
        status = cache_cleaner.get_cleanup_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({'error': str(e)}), 500

@cache_bp.route('/api/cache/sessions/cleanup', methods=['POST'])
@login_required
def cleanup_sessions_only():
    """Limpeza apenas de sessões expiradas"""
    try:
        if not cache_cleaner:
            return jsonify({'error': 'Cache cleaner não inicializado'}), 500
        
        # Verificar se usuário é admin
        if session.get('user_type') != 'administrador':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        
        count = cache_cleaner.cleanup_expired_sessions()
        return jsonify({
            'success': True,
            'message': f'{count} sessões expiradas removidas'
        })
    except Exception as e:
        logger.error(f"Erro na limpeza de sessões: {e}")
        return jsonify({'error': str(e)}), 500

@cache_bp.route('/api/cache/files/cleanup', methods=['POST'])
@login_required
def cleanup_temp_files_only():
    """Limpeza apenas de arquivos temporários"""
    try:
        if not cache_cleaner:
            return jsonify({'error': 'Cache cleaner não inicializado'}), 500
        
        # Verificar se usuário é admin
        if session.get('user_type') != 'administrador':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        
        count = cache_cleaner.cleanup_temp_files()
        return jsonify({
            'success': True,
            'message': f'{count} arquivos temporários removidos'
        })
    except Exception as e:
        logger.error(f"Erro na limpeza de arquivos: {e}")
        return jsonify({'error': str(e)}), 500

@cache_bp.route('/api/cache/database/optimize', methods=['POST'])
@login_required
def optimize_database_only():
    """Otimização apenas do banco de dados"""
    try:
        if not cache_cleaner:
            return jsonify({'error': 'Cache cleaner não inicializado'}), 500
        
        # Verificar se usuário é admin
        if session.get('user_type') != 'administrador':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        
        success = cache_cleaner.optimize_sqlite_database()
        if success:
            return jsonify({
                'success': True,
                'message': 'Banco de dados otimizado com sucesso'
            })
        else:
            return jsonify({'error': 'Falha na otimização do banco'}), 500
    except Exception as e:
        logger.error(f"Erro na otimização: {e}")
        return jsonify({'error': str(e)}), 500

# Rotas web para interface administrativa
@cache_bp.route('/admin/cache-management')
@login_required
@admin_required
def cache_management_page():
    """Página de gerenciamento de cache"""
    try:
        status = cache_cleaner.get_cleanup_status() if cache_cleaner else {}
        return render_template('admin/cache_management.html', status=status)
    except Exception as e:
        flash(f'Erro ao carregar página: {e}', 'error')
        return redirect(url_for('helpdesk.dashboard_admin'))

@cache_bp.route('/admin/cache/manual-cleanup', methods=['POST'])
@login_required
@admin_required
def manual_cleanup_web():
    """Limpeza manual via interface web"""
    try:
        if not cache_cleaner:
            flash('Sistema de limpeza não disponível', 'error')
            return redirect(url_for('cache_management.cache_management_page'))
        
        results = cache_cleaner.run_full_cleanup()
        
        message = f"Limpeza concluída! "
        message += f"Sessões: {results.get('sessions', 0)}, "
        message += f"Arquivos temp: {results.get('temp_files', 0)}, "
        message += f"Logs: {results.get('logs', 0)}, "
        message += f"DB otimizado: {'Sim' if results.get('database_optimized', False) else 'Não'}"
        
        flash(message, 'success')
    except Exception as e:
        flash(f'Erro na limpeza: {e}', 'error')
    
    return redirect(url_for('cache_management.cache_management_page'))