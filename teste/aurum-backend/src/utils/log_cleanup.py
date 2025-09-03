from datetime import datetime, timedelta
from src.models.activity_log import ActivityLog
from src.models.user import db
import threading
import time
# import schedule  # Comentado - instalar se necessário: pip install schedule

class LogCleanupManager:
    """Gerenciador de limpeza automática de logs"""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler_thread = None
        self.running = False
        
        # Configurações padrão
        self.config = {
            'enabled': True,
            'retention_days': 90,  # Manter logs por 90 dias
            'cleanup_interval_hours': 24,  # Executar limpeza a cada 24h
            'batch_size': 1000,  # Deletar em lotes de 1000
            'keep_critical_logs': True,  # Manter logs críticos (erros, logins)
            'critical_retention_days': 180  # Manter logs críticos por 6 meses
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa com a aplicação Flask"""
        self.app = app
        
        # Carregar configurações do app se existirem
        self.config.update({
            'enabled': app.config.get('LOG_CLEANUP_ENABLED', self.config['enabled']),
            'retention_days': app.config.get('LOG_RETENTION_DAYS', self.config['retention_days']),
            'cleanup_interval_hours': app.config.get('LOG_CLEANUP_INTERVAL_HOURS', self.config['cleanup_interval_hours']),
            'batch_size': app.config.get('LOG_CLEANUP_BATCH_SIZE', self.config['batch_size']),
            'keep_critical_logs': app.config.get('LOG_KEEP_CRITICAL', self.config['keep_critical_logs']),
            'critical_retention_days': app.config.get('LOG_CRITICAL_RETENTION_DAYS', self.config['critical_retention_days'])
        })
        
        # Registrar comando CLI se necessário
        self.register_cli_commands(app)
        
        # Iniciar scheduler automático se habilitado
        if self.config['enabled']:
            self.start_scheduler()
    
    def register_cli_commands(self, app):
        """Registra comandos CLI para gerenciamento de logs"""
        @app.cli.command('cleanup-logs')
        def cleanup_logs_command():
            """Comando CLI para executar limpeza de logs manualmente"""
            with app.app_context():
                deleted = self.cleanup_old_logs()
                print(f"Logs limpos: {deleted} registros removidos.")
        
        @app.cli.command('log-stats')
        def log_stats_command():
            """Comando CLI para mostrar estatísticas de logs"""
            with app.app_context():
                stats = self.get_log_statistics()
                print("=== Estatísticas de Logs ===")
                print(f"Total de logs: {stats['total']}")
                print(f"Logs dos últimos 7 dias: {stats['last_7_days']}")
                print(f"Logs dos últimos 30 dias: {stats['last_30_days']}")
                print(f"Logs mais antigos que {self.config['retention_days']} dias: {stats['old_logs']}")
                print(f"Logs críticos: {stats['critical_logs']}")
    
    def start_scheduler(self):
        """Inicia o scheduler de limpeza automática"""
        if self.running:
            return
        
        self.running = True
        
        # Thread simples para executar limpeza periódica
        def run_scheduler():
            next_cleanup = time.time() + (self.config['cleanup_interval_hours'] * 3600)
            
            while self.running:
                if time.time() >= next_cleanup:
                    self._scheduled_cleanup()
                    next_cleanup = time.time() + (self.config['cleanup_interval_hours'] * 3600)
                
                time.sleep(300)  # Verificar a cada 5 minutos
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print(f"Log cleanup scheduler iniciado - executará a cada {self.config['cleanup_interval_hours']}h")
    
    def stop_scheduler(self):
        """Para o scheduler de limpeza"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
    
    def _scheduled_cleanup(self):
        """Executa limpeza agendada"""
        if self.app:
            with self.app.app_context():
                try:
                    deleted = self.cleanup_old_logs()
                    if deleted > 0:
                        print(f"Log cleanup automático: {deleted} registros removidos.")
                except Exception as e:
                    print(f"Erro na limpeza automática de logs: {e}")
    
    def cleanup_old_logs(self):
        """Executa limpeza de logs antigos"""
        if not self.config['enabled']:
            return 0
        
        total_deleted = 0
        
        # Data limite para logs normais
        normal_cutoff_date = datetime.utcnow() - timedelta(days=self.config['retention_days'])
        
        # Data limite para logs críticos (se configurado)
        critical_cutoff_date = None
        if self.config['keep_critical_logs']:
            critical_cutoff_date = datetime.utcnow() - timedelta(days=self.config['critical_retention_days'])
        
        try:
            # Query para logs que devem ser removidos
            query = ActivityLog.query.filter(ActivityLog.timestamp < normal_cutoff_date)
            
            # Se manter logs críticos, excluí-los da limpeza normal
            if self.config['keep_critical_logs']:
                critical_actions = ['ERROR', 'LOGIN_FAILED', 'DELETE']
                query = query.filter(~ActivityLog.action.in_(critical_actions))
            
            # Contar quantos serão removidos
            total_to_delete = query.count()
            
            if total_to_delete == 0:
                return 0
            
            # Deletar em lotes para não sobrecarregar o banco
            batch_size = self.config['batch_size']
            
            while True:
                # Buscar um lote
                batch = query.limit(batch_size).all()
                
                if not batch:
                    break
                
                # Deletar o lote
                for log in batch:
                    db.session.delete(log)
                
                db.session.commit()
                total_deleted += len(batch)
                
                print(f"Logs limpos: {total_deleted}/{total_to_delete}")
                
                # Pequena pausa para não sobrecarregar
                time.sleep(0.1)
            
            # Limpar logs críticos muito antigos
            if critical_cutoff_date:
                critical_query = ActivityLog.query.filter(
                    ActivityLog.timestamp < critical_cutoff_date,
                    ActivityLog.action.in_(['ERROR', 'LOGIN_FAILED', 'DELETE'])
                )
                
                critical_count = critical_query.count()
                if critical_count > 0:
                    for log in critical_query.all():
                        db.session.delete(log)
                    db.session.commit()
                    total_deleted += critical_count
                    print(f"Logs críticos antigos removidos: {critical_count}")
            
            # Log da própria limpeza
            from src.utils.activity_logger import activity_logger
            activity_logger.log_activity(
                action="CLEANUP",
                module="system",
                description=f"Limpeza automática removeu {total_deleted} logs antigos",
                extra_data={
                    'deleted_count': total_deleted,
                    'retention_days': self.config['retention_days'],
                    'critical_retention_days': self.config['critical_retention_days'],
                    'cutoff_date': normal_cutoff_date.isoformat()
                }
            )
            
        except Exception as e:
            print(f"Erro durante limpeza de logs: {e}")
            db.session.rollback()
            raise
        
        return total_deleted
    
    def get_log_statistics(self):
        """Retorna estatísticas dos logs"""
        now = datetime.utcnow()
        
        stats = {
            'total': ActivityLog.query.count(),
            'last_7_days': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=7)
            ).count(),
            'last_30_days': ActivityLog.query.filter(
                ActivityLog.timestamp >= now - timedelta(days=30)
            ).count(),
            'old_logs': ActivityLog.query.filter(
                ActivityLog.timestamp < now - timedelta(days=self.config['retention_days'])
            ).count(),
            'critical_logs': ActivityLog.query.filter(
                ActivityLog.action.in_(['ERROR', 'LOGIN_FAILED', 'DELETE'])
            ).count()
        }
        
        # Estatísticas por módulo
        from sqlalchemy import func
        module_stats = db.session.query(
            ActivityLog.module,
            func.count(ActivityLog.id).label('count')
        ).group_by(ActivityLog.module).order_by(func.count(ActivityLog.id).desc()).all()
        
        stats['by_module'] = [{'module': module, 'count': count} for module, count in module_stats]
        
        # Estatísticas por ação
        action_stats = db.session.query(
            ActivityLog.action,
            func.count(ActivityLog.id).label('count')
        ).group_by(ActivityLog.action).order_by(func.count(ActivityLog.id).desc()).all()
        
        stats['by_action'] = [{'action': action, 'count': count} for action, count in action_stats]
        
        return stats
    
    def optimize_log_table(self):
        """Otimiza a tabela de logs (reconstrução de índices, etc)"""
        try:
            # SQLite: VACUUM para otimizar
            if 'sqlite' in str(db.engine.url):
                db.engine.execute('VACUUM')
            
            # PostgreSQL: ANALYZE para atualizar estatísticas
            elif 'postgresql' in str(db.engine.url):
                db.engine.execute('ANALYZE activity_logs')
            
            return True
            
        except Exception as e:
            print(f"Erro ao otimizar tabela de logs: {e}")
            return False

# Instância global do gerenciador
log_cleanup_manager = LogCleanupManager()