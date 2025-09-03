from flask import Blueprint, render_template, request, jsonify, session
from src.models.activity_log import ActivityLog
from src.models.helpdesk_models import Usuario
from src.models.user import db
from src.utils import login_required, admin_required
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from src.utils.activity_logger import activity_logger

activity_logs_bp = Blueprint('activity_logs', __name__)

@activity_logs_bp.route('/logs')
@login_required
@admin_required
def listar_logs():
    """Interface principal para visualizar logs de atividade"""
    # Parâmetros de filtro
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action_filter = request.args.get('action', '')
    module_filter = request.args.get('module', '')
    user_filter = request.args.get('user_id', '', type=str)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('search', '')
    
    # Log do acesso à página de logs
    activity_logger.log_view(
        module="system",
        description="Acessou página de logs de atividade"
    )
    
    # Construir query base
    query = ActivityLog.query
    
    # Aplicar filtros
    if action_filter:
        query = query.filter(ActivityLog.action == action_filter.upper())
    
    if module_filter:
        query = query.filter(ActivityLog.module == module_filter.lower())
    
    if user_filter:
        if user_filter.isdigit():
            query = query.filter(ActivityLog.user_id == int(user_filter))
        else:
            query = query.filter(
                or_(
                    ActivityLog.user_name.ilike(f'%{user_filter}%'),
                    ActivityLog.user_email.ilike(f'%{user_filter}%')
                )
            )
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ActivityLog.timestamp >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ActivityLog.timestamp < date_to_obj)
        except ValueError:
            pass
    
    if search:
        query = query.filter(
            or_(
                ActivityLog.description.ilike(f'%{search}%'),
                ActivityLog.user_name.ilike(f'%{search}%'),
                ActivityLog.endpoint.ilike(f'%{search}%')
            )
        )
    
    # Ordenar por timestamp decrescente
    query = query.order_by(ActivityLog.timestamp.desc())
    
    # Paginar
    logs_pagination = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # Buscar dados para os filtros
    actions = db.session.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all()
    modules = db.session.query(ActivityLog.module).distinct().order_by(ActivityLog.module).all()
    
    actions = [action[0] for action in actions if action[0]]
    modules = [module[0] for module in modules if module[0]]
    
    return render_template('activity_logs.html',
                         logs=logs_pagination.items,
                         pagination=logs_pagination,
                         actions=actions,
                         modules=modules,
                         current_filters={
                             'action': action_filter,
                             'module': module_filter,
                             'user_id': user_filter,
                             'date_from': date_from,
                             'date_to': date_to,
                             'search': search,
                             'per_page': per_page
                         })

@activity_logs_bp.route('/logs/api')
@login_required
@admin_required
def logs_api():
    """API JSON para logs (útil para AJAX/dashboard)"""
    limit = request.args.get('limit', 10, type=int)
    action_filter = request.args.get('action', '')
    module_filter = request.args.get('module', '')
    
    query = ActivityLog.query
    
    if action_filter:
        query = query.filter(ActivityLog.action == action_filter.upper())
    
    if module_filter:
        query = query.filter(ActivityLog.module == module_filter.lower())
    
    # Últimos logs
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
    
    return jsonify({
        'logs': [log.to_dict() for log in logs],
        'total': query.count()
    })

@activity_logs_bp.route('/logs/stats')
@login_required
@admin_required
def logs_stats():
    """Estatísticas dos logs para dashboard"""
    from sqlalchemy import func
    
    # Logs das últimas 24 horas
    last_24h = datetime.utcnow() - timedelta(hours=24)
    logs_24h = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h).count()
    
    # Logs da última semana
    last_week = datetime.utcnow() - timedelta(days=7)
    logs_week = ActivityLog.query.filter(ActivityLog.timestamp >= last_week).count()
    
    # Top 5 ações
    top_actions = db.session.query(
        ActivityLog.action, 
        func.count(ActivityLog.action).label('count')
    ).group_by(ActivityLog.action).order_by(func.count(ActivityLog.action).desc()).limit(5).all()
    
    # Top 5 módulos
    top_modules = db.session.query(
        ActivityLog.module,
        func.count(ActivityLog.module).label('count')
    ).group_by(ActivityLog.module).order_by(func.count(ActivityLog.module).desc()).limit(5).all()
    
    # Top 5 usuários ativos
    top_users = db.session.query(
        ActivityLog.user_name,
        func.count(ActivityLog.user_id).label('count')
    ).filter(ActivityLog.user_name.isnot(None)).group_by(
        ActivityLog.user_name
    ).order_by(func.count(ActivityLog.user_id).desc()).limit(5).all()
    
    # Atividade por hora (últimas 24 horas)
    activity_by_hour = db.session.query(
        func.date_format(ActivityLog.timestamp, '%H').label('hour'),
        func.count(ActivityLog.id).label('count')
    ).filter(ActivityLog.timestamp >= last_24h).group_by(
        func.date_format(ActivityLog.timestamp, '%H')
    ).order_by('hour').all()
    
    return jsonify({
        'logs_24h': logs_24h,
        'logs_week': logs_week,
        'total_logs': ActivityLog.query.count(),
        'top_actions': [{'action': action, 'count': count} for action, count in top_actions],
        'top_modules': [{'module': module, 'count': count} for module, count in top_modules],
        'top_users': [{'user': user, 'count': count} for user, count in top_users],
        'activity_by_hour': [{'hour': hour, 'count': count} for hour, count in activity_by_hour]
    })

@activity_logs_bp.route('/logs/<int:log_id>')
@login_required
@admin_required
def detalhe_log(log_id):
    """Visualizar detalhes de um log específico"""
    log = ActivityLog.query.get_or_404(log_id)
    
    # Log do acesso ao detalhe
    activity_logger.log_view(
        module="system",
        entity_type="ActivityLog",
        entity_id=log_id,
        description=f"Visualizou detalhes do log ID {log_id}"
    )
    
    return render_template('detalhe_log.html', log=log)

@activity_logs_bp.route('/logs/export')
@login_required
@admin_required
def exportar_logs():
    """Exportar logs para CSV"""
    import csv
    import io
    from flask import make_response
    
    # Parâmetros de filtro (mesmos da listagem)
    action_filter = request.args.get('action', '')
    module_filter = request.args.get('module', '')
    user_filter = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    limit = request.args.get('limit', 1000, type=int)
    
    # Aplicar os mesmos filtros da listagem
    query = ActivityLog.query
    
    if action_filter:
        query = query.filter(ActivityLog.action == action_filter.upper())
    if module_filter:
        query = query.filter(ActivityLog.module == module_filter.lower())
    if user_filter:
        if user_filter.isdigit():
            query = query.filter(ActivityLog.user_id == int(user_filter))
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ActivityLog.timestamp >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ActivityLog.timestamp < date_to_obj)
        except ValueError:
            pass
    
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
    
    # Log da exportação
    activity_logger.log_activity(
        action="EXPORT",
        module="system",
        description=f"Exportou {len(logs)} logs para CSV",
        extra_data={
            'filters': {
                'action': action_filter,
                'module': module_filter,
                'user_filter': user_filter,
                'date_from': date_from,
                'date_to': date_to
            },
            'record_count': len(logs)
        }
    )
    
    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cabeçalhos
    writer.writerow([
        'ID', 'Timestamp', 'Usuário', 'Tipo Usuário', 'Email', 'IP',
        'Ação', 'Módulo', 'Entidade', 'ID Entidade', 'Descrição',
        'Endpoint', 'Método', 'Status', 'Tempo Resposta (ms)'
    ])
    
    # Dados
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else '',
            log.user_name or '',
            log.user_type or '',
            log.user_email or '',
            log.ip_address or '',
            log.action or '',
            log.module or '',
            log.entity_type or '',
            log.entity_id or '',
            log.description or '',
            log.endpoint or '',
            log.method or '',
            log.status_code or '',
            log.response_time or ''
        ])
    
    # Preparar resposta
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=activity_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response