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
    
    def optimize_sqlite_database(self, create_backup=False):
        """Otimiza o banco SQLite (VACUUM e ANALYZE)"""
        try:
            if not self.db_path or not os.path.exists(self.db_path):
                return False

            backup_path = None
            if create_backup:
                # Backup apenas se solicitado explicitamente
                backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                with sqlite3.connect(self.db_path) as source:
                    with sqlite3.connect(backup_path) as backup:
                        source.backup(backup)

                logger.info(f"Backup criado: {backup_path}")

            # Otimização sem backup automático
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('VACUUM')
                conn.execute('ANALYZE')
                conn.commit()

            logger.info("Banco SQLite otimizado com sucesso")
            return True
        except Exception as e:
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)  # Remove backup se houve erro
            logger.error(f"Erro na otimização do banco: {e}")
            return False
    
    def cleanup_old_database_backups(self, days_old=365):
        """Remove backups antigos do banco (padrão: 1 ano)"""
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

            logger.info(f"Limpeza de backups antigos: {cleaned_count} arquivos removidos (mais de {days_old} dias)")
            return cleaned_count
        except Exception as e:
            logger.error(f"Erro na limpeza de backups: {e}")
            return 0

    def create_annual_backup(self):
        """Cria backup anual do banco de dados"""
        try:
            if not self.db_path or not os.path.exists(self.db_path):
                return False

            current_year = datetime.now().year
            backup_path = f"{self.db_path}.backup_anual_{current_year}"

            # Verificar se já existe backup do ano atual
            if os.path.exists(backup_path):
                logger.info(f"Backup anual {current_year} já existe")
                return True

            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)

            logger.info(f"Backup anual criado: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar backup anual: {e}")
            return False
    
    def run_full_cleanup(self):
        """Executa limpeza completa do sistema (sem backup automático)"""
        logger.info("Iniciando limpeza automática do sistema...")

        results = {
            'sessions': self.cleanup_expired_sessions(),
            'temp_files': self.cleanup_temp_files(),
            'logs': self.cleanup_old_logs(),
            'database_optimized': self.optimize_sqlite_database(create_backup=False),  # Sem backup automático
            'old_backups': self.cleanup_old_database_backups()
        }

        logger.info("Limpeza automática concluída")
        logger.info(f"Resultados: {results}")
        return results
    
    def check_annual_backup(self):
        """Verifica se precisa fazer backup anual (1º de janeiro)"""
        now = datetime.now()
        if now.month == 1 and now.day == 1:
            # Só executa uma vez no dia 1º de janeiro
            current_year = now.year
            backup_path = f"{self.db_path}.backup_anual_{current_year}"
            if not os.path.exists(backup_path):
                logger.info("Executando backup anual...")
                return self.create_annual_backup()
        return False

    def start_scheduler(self):
        """Inicia o agendador de limpeza automática"""
        # Limpeza diária às 2:00 AM (sem backup)
        schedule.every().day.at("02:00").do(self.run_full_cleanup)

        # Verificação de backup anual diariamente às 3:30 AM
        schedule.every().day.at("03:30").do(self.check_annual_backup)

        # Limpeza de sessões a cada 12 horas (reduzido de 6h)
        schedule.every(12).hours.do(self.cleanup_expired_sessions)

        # Limpeza de arquivos temporários diariamente às 3:00 AM
        schedule.every().day.at("03:00").do(self.cleanup_temp_files)

        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(3600)  # Verifica a cada hora

        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

        logger.info("Scheduler de limpeza automática iniciado - Backup anual configurado")
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