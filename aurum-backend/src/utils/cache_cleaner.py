import os
import time
import logging
import sqlite3
import tempfile
import glob
from datetime import datetime, timedelta
from threading import Thread
import schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheCleaner:
    def __init__(self, app=None):
        self.app = app
        self.db_path = None
        self.temp_dir = tempfile.gettempdir()
        self.logs_dir = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        self.logs_dir = os.path.join(os.path.dirname(app.instance_path), 'logs')
        
        # Criar diretório de logs se não existir
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)
    
    def cleanup_expired_sessions(self, hours_old=24):
        """Remove sessões Flask expiradas há mais de X horas"""
        try:
            session_dir = os.path.join(tempfile.gettempdir(), 'flask_sessions')
            if not os.path.exists(session_dir):
                return
            
            cutoff_time = time.time() - (hours_old * 3600)
            cleaned_count = 0
            
            for session_file in glob.glob(os.path.join(session_dir, 'sess_*')):
                if os.path.getmtime(session_file) < cutoff_time:
                    try:
                        os.remove(session_file)
                        cleaned_count += 1
                    except OSError:
                        pass
            
            logger.info(f"Limpeza de sessões: {cleaned_count} arquivos removidos")
            return cleaned_count
        except Exception as e:
            logger.error(f"Erro na limpeza de sessões: {e}")
            return 0
    
    def cleanup_temp_files(self, hours_old=24):
        """Remove arquivos temporários de relatórios antigos"""
        try:
            patterns = [
                'relatorio_*.pdf',
                'relatorio_*.xlsx',
                'temp_export_*.pdf',
                'temp_export_*.xlsx'
            ]
            
            cutoff_time = time.time() - (hours_old * 3600)
            cleaned_count = 0
            
            for pattern in patterns:
                for temp_file in glob.glob(os.path.join(self.temp_dir, pattern)):
                    try:
                        if os.path.getmtime(temp_file) < cutoff_time:
                            os.remove(temp_file)
                            cleaned_count += 1
                    except OSError:
                        pass
            
            logger.info(f"Limpeza de arquivos temporários: {cleaned_count} arquivos removidos")
            return cleaned_count
        except Exception as e:
            logger.error(f"Erro na limpeza de arquivos temporários: {e}")
            return 0
    
    def cleanup_old_logs(self, days_old=30):
        """Remove logs antigos"""
        try:
            if not self.logs_dir or not os.path.exists(self.logs_dir):
                return 0
            
            cutoff_time = time.time() - (days_old * 24 * 3600)
            cleaned_count = 0
            
            for log_file in glob.glob(os.path.join(self.logs_dir, '*.log*')):
                try:
                    if os.path.getmtime(log_file) < cutoff_time:
                        os.remove(log_file)
                        cleaned_count += 1
                except OSError:
                    pass
            
            logger.info(f"Limpeza de logs: {cleaned_count} arquivos removidos")
            return cleaned_count
        except Exception as e:
            logger.error(f"Erro na limpeza de logs: {e}")
            return 0
    
    def optimize_sqlite_database(self):
        """Otimiza o banco SQLite (VACUUM e ANALYZE)"""
        try:
            if not self.db_path or not os.path.exists(self.db_path):
                return False
            
            # Backup básico antes da otimização
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            # Otimização
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('VACUUM')
                conn.execute('ANALYZE')
                conn.commit()
            
            # Remove backup se otimização foi bem-sucedida
            os.remove(backup_path)
            
            logger.info("Banco SQLite otimizado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro na otimização do banco: {e}")
            return False
    
    def cleanup_old_database_backups(self, days_old=7):
        """Remove backups antigos do banco"""
        try:
            if not self.db_path:
                return 0
            
            db_dir = os.path.dirname(self.db_path)
            backup_pattern = os.path.join(db_dir, "*.backup_*")
            
            cutoff_time = time.time() - (days_old * 24 * 3600)
            cleaned_count = 0
            
            for backup_file in glob.glob(backup_pattern):
                try:
                    if os.path.getmtime(backup_file) < cutoff_time:
                        os.remove(backup_file)
                        cleaned_count += 1
                except OSError:
                    pass
            
            logger.info(f"Limpeza de backups: {cleaned_count} arquivos removidos")
            return cleaned_count
        except Exception as e:
            logger.error(f"Erro na limpeza de backups: {e}")
            return 0
    
    def run_full_cleanup(self):
        """Executa limpeza completa do sistema"""
        logger.info("Iniciando limpeza automática do sistema...")
        
        results = {
            'sessions': self.cleanup_expired_sessions(),
            'temp_files': self.cleanup_temp_files(),
            'logs': self.cleanup_old_logs(),
            'database_optimized': self.optimize_sqlite_database(),
            'old_backups': self.cleanup_old_database_backups()
        }
        
        logger.info("Limpeza automática concluída")
        logger.info(f"Resultados: {results}")
        return results
    
    def start_scheduler(self):
        """Inicia o agendador de limpeza automática"""
        # Limpeza diária às 2:00 AM
        schedule.every().day.at("02:00").do(self.run_full_cleanup)
        
        # Limpeza de sessões a cada 6 horas
        schedule.every(6).hours.do(self.cleanup_expired_sessions)
        
        # Limpeza de arquivos temporários a cada 12 horas
        schedule.every(12).hours.do(self.cleanup_temp_files)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
        
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Scheduler de limpeza automática iniciado")
        return scheduler_thread
    
    def get_cleanup_status(self):
        """Retorna status atual do sistema para limpeza"""
        try:
            status = {
                'temp_files_count': len(glob.glob(os.path.join(self.temp_dir, 'relatorio_*'))),
                'database_size_mb': 0,
                'last_cleanup': 'Nunca executado'
            }
            
            if self.db_path and os.path.exists(self.db_path):
                status['database_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            return status
        except Exception as e:
            logger.error(f"Erro ao obter status: {e}")
            return {}