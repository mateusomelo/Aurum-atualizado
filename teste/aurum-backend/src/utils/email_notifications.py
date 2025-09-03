import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from flask import current_app
import logging

class EmailNotifier:
    def __init__(self):
        # Configurar logging
        self.logger = logging.getLogger(__name__)
    
    def _get_email_config(self):
        """
        Busca configurações de email das variáveis de ambiente
        """
        return {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'email_user': os.getenv('EMAIL_USER', ''),
            'email_password': os.getenv('EMAIL_PASSWORD', ''),
            'from_name': os.getenv('EMAIL_FROM_NAME', 'Sistema Helpdesk Aurum'),
            'use_tls': True
        }
        
    def _send_email(self, to_emails, subject, html_content, plain_content=None, timeout=30):
        """
        Envia email para uma lista de destinatários com timeout e melhor diagnóstico
        """
        import socket
        
        # Buscar configurações do banco de dados
        email_config = self._get_email_config()
        
        if not email_config['email_user'] or not email_config['email_password']:
            self.logger.error("Configurações de email não definidas (usuário ou senha vazios)")
            return False
            
        if not to_emails:
            self.logger.error("Nenhum destinatário especificado")
            return False
            
        # Se for lista, converter para string
        if isinstance(to_emails, list):
            recipients = to_emails
            recipients_str = ', '.join(to_emails)
        else:
            recipients = [to_emails]
            recipients_str = to_emails
        
        server = None
        try:
            # Configurar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{email_config['from_name']} <{email_config['email_user']}>"
            msg['To'] = recipients_str
            
            # Adicionar conteúdo texto plano
            if plain_content:
                plain_part = MIMEText(plain_content, 'plain', 'utf-8')
                msg.attach(plain_part)
            
            # Adicionar conteúdo HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Configurar timeout para socket
            socket.setdefaulttimeout(timeout)
            
            # Conectar ao servidor SMTP
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'], timeout=timeout)
            
            # Debug do servidor desabilitado
            server.set_debuglevel(0)
            
            if email_config['use_tls']:
                server.starttls()
            
            server.login(email_config['email_user'], email_config['email_password'])
            
            # Enviar email
            server.send_message(msg, to_addrs=recipients)
            
            server.quit()
            return True
            
        except socket.timeout:
            self.logger.error(f"Timeout na conexão SMTP ({timeout}s). Verifique se o servidor está acessível.")
            return False
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"Erro de autenticação: {str(e)}")
            self.logger.error("Dica: Para Gmail, use uma 'Senha de App' em vez da senha normal.")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            self.logger.error(f"Email do destinatário rejeitado: {str(e)}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            self.logger.error(f"Servidor desconectou: {str(e)}")
            return False
        except smtplib.SMTPConnectError as e:
            self.logger.error(f"Erro de conexão SMTP: {str(e)}")
            self.logger.error("Verifique se o servidor e porta estão corretos.")
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado ao enviar email: {str(e)}")
            self.logger.error(f"Tipo do erro: {type(e).__name__}")
            return False
        finally:
            # Garantir que a conexão seja fechada
            if server:
                try:
                    server.quit()
                except:
                    pass
            # Restaurar timeout padrão
            socket.setdefaulttimeout(None)
    
    def _get_email_template(self, template_type, **kwargs):
        """
        Retorna templates de email baseado no tipo
        """
        templates = {
            'novo_chamado_cliente': {
                'subject': f"Chamado #{kwargs['chamado_id']} Criado - {kwargs['titulo']}",
                'html': f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2c5aa0;">Chamado Criado com Sucesso</h2>
                        
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Número do Chamado:</strong> #{kwargs['chamado_id']}</p>
                            <p><strong>Título:</strong> {kwargs['titulo']}</p>
                            <p><strong>Prioridade:</strong> {kwargs['prioridade'].title()}</p>
                            <p><strong>Status:</strong> {kwargs['status'].replace('_', ' ').title()}</p>
                            <p><strong>Data de Abertura:</strong> {kwargs['data_abertura']}</p>
                        </div>
                        
                        <div style="margin: 20px 0;">
                            <p><strong>Descrição:</strong></p>
                            <div style="background-color: #ffffff; padding: 10px; border-left: 4px solid #2c5aa0; margin: 10px 0;">
                                {kwargs['descricao']}
                            </div>
                        </div>
                        
                        <p>Seu chamado foi registrado em nosso sistema e será atendido em breve por nossa equipe técnica.</p>
                        
                        <div style="background-color: #e7f3ff; padding: 10px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Próximos Passos:</strong></p>
                            <ul>
                                <li>Um técnico será designado para seu chamado</li>
                                <li>Você receberá um email quando o status for atualizado</li>
                                <li>Acompanhe o progresso através do sistema</li>
                            </ul>
                        </div>
                        
                        <hr style="margin: 30px 0;">
                        <p style="font-size: 12px; color: #666;">
                            Este é um email automático do Sistema Helpdesk Aurum.<br>
                            Por favor, não responda a este email.
                        </p>
                    </div>
                </body>
                </html>
                """
            },
            
            'novo_chamado_admin_tecnico': {
                'subject': f"Novo Chamado #{kwargs['chamado_id']} - {kwargs['titulo']}",
                'html': f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #d73027;">Novo Chamado Aberto</h2>
                        
                        <div style="background-color: #fff2f2; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #d73027;">
                            <p><strong>Chamado:</strong> #{kwargs['chamado_id']}</p>
                            <p><strong>Título:</strong> {kwargs['titulo']}</p>
                            <p><strong>Cliente:</strong> {kwargs['cliente_nome']} ({kwargs['cliente_email']})</p>
                            <p><strong>Empresa:</strong> {kwargs['empresa']}</p>
                            <p><strong>Prioridade:</strong> <span style="color: {'#d73027' if kwargs['prioridade'] == 'alta' else '#f57c00' if kwargs['prioridade'] == 'media' else '#388e3c'};">{kwargs['prioridade'].upper()}</span></p>
                            <p><strong>Data de Abertura:</strong> {kwargs['data_abertura']}</p>
                        </div>
                        
                        <div style="margin: 20px 0;">
                            <p><strong>Descrição do Problema:</strong></p>
                            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                                {kwargs['descricao']}
                            </div>
                        </div>
                        
                        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Ação Necessária:</strong></p>
                            <p>Este chamado precisa ser atribuído a um técnico para atendimento.</p>
                            <p><strong>Acesse o sistema</strong> para visualizar e atribuir este chamado.</p>
                        </div>
                        
                        <hr style="margin: 30px 0;">
                        <p style="font-size: 12px; color: #666;">
                            Sistema Helpdesk Aurum - Notificação Automática<br>
                            Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
                        </p>
                    </div>
                </body>
                </html>
                """
            },
            
            'chamado_atribuido': {
                'subject': f"Chamado #{kwargs['chamado_id']} Atribuído a Você",
                'html': f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #f57c00;">Chamado Atribuído</h2>
                        
                        <div style="background-color: #fff8e1; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #f57c00;">
                            <p>Olá <strong>{kwargs['tecnico_nome']}</strong>,</p>
                            <p>Um novo chamado foi atribuído a você para atendimento:</p>
                        </div>
                        
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Número do Chamado:</strong> #{kwargs['chamado_id']}</p>
                            <p><strong>Título:</strong> {kwargs['titulo']}</p>
                            <p><strong>Cliente:</strong> {kwargs['cliente_nome']} ({kwargs['cliente_email']})</p>
                            <p><strong>Empresa:</strong> {kwargs['empresa']}</p>
                            <p><strong>Prioridade:</strong> <span style="color: {'#d73027' if kwargs['prioridade'] == 'alta' else '#f57c00' if kwargs['prioridade'] == 'media' else '#388e3c'};">{kwargs['prioridade'].upper()}</span></p>
                            <p><strong>Data de Abertura:</strong> {kwargs['data_abertura']}</p>
                        </div>
                        
                        <div style="margin: 20px 0;">
                            <p><strong>Descrição:</strong></p>
                            <div style="background-color: #ffffff; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">
                                {kwargs['descricao']}
                            </div>
                        </div>
                        
                        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Próximos Passos:</strong></p>
                            <ol>
                                <li>Acesse o sistema para ver mais detalhes</li>
                                <li>Entre em contato com o cliente se necessário</li>
                                <li>Mantenha o status do chamado atualizado</li>
                                <li>Documente as ações realizadas</li>
                            </ol>
                        </div>
                        
                        <hr style="margin: 30px 0;">
                        <p style="font-size: 12px; color: #666;">
                            Sistema Helpdesk Aurum - Notificação de Atribuição<br>
                            Atribuído em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
                        </p>
                    </div>
                </body>
                </html>
                """
            }
        }
        
        return templates.get(template_type, {})
    
    def notify_new_ticket_to_client(self, chamado, cliente):
        """
        Notifica o cliente que criou o chamado
        """
        template = self._get_email_template('novo_chamado_cliente',
            chamado_id=chamado.id,
            titulo=chamado.titulo,
            prioridade=chamado.prioridade,
            status=chamado.status,
            data_abertura=chamado.data_criacao.strftime('%d/%m/%Y às %H:%M'),
            descricao=chamado.descricao
        )
        
        return self._send_email(
            to_emails=cliente.email,
            subject=template['subject'],
            html_content=template['html']
        )
    
    def notify_new_ticket_to_admins_and_technicians(self, chamado, cliente, empresa):
        """
        Notifica administradores e técnicos sobre novo chamado
        """
        from src.models.helpdesk_models import Usuario
        
        # Buscar todos os administradores e técnicos ativos
        admin_tecnicos = Usuario.query.filter(
            Usuario.ativo == True,
            Usuario.tipo_usuario.in_(['administrador', 'tecnico'])
        ).all()
        
        if not admin_tecnicos:
            return False
        
        # Preparar lista de emails
        emails = [user.email for user in admin_tecnicos if user.email]
        
        template = self._get_email_template('novo_chamado_admin_tecnico',
            chamado_id=chamado.id,
            titulo=chamado.titulo,
            cliente_nome=cliente.nome,
            cliente_email=cliente.email,
            empresa=empresa.nome_empresa if empresa else 'N/A',
            prioridade=chamado.prioridade,
            data_abertura=chamado.data_criacao.strftime('%d/%m/%Y às %H:%M'),
            descricao=chamado.descricao
        )
        
        return self._send_email(
            to_emails=emails,
            subject=template['subject'],
            html_content=template['html']
        )
    
    def notify_ticket_assigned_to_technician(self, chamado, tecnico, cliente, empresa):
        """
        Notifica o técnico quando um chamado é atribuído a ele
        """
        template = self._get_email_template('chamado_atribuido',
            chamado_id=chamado.id,
            titulo=chamado.titulo,
            tecnico_nome=tecnico.nome,
            cliente_nome=cliente.nome,
            cliente_email=cliente.email,
            empresa=empresa.nome_empresa if empresa else 'N/A',
            prioridade=chamado.prioridade,
            data_abertura=chamado.data_criacao.strftime('%d/%m/%Y às %H:%M'),
            descricao=chamado.descricao
        )
        
        return self._send_email(
            to_emails=tecnico.email,
            subject=template['subject'],
            html_content=template['html']
        )

# Instância global do notificador
email_notifier = EmailNotifier()