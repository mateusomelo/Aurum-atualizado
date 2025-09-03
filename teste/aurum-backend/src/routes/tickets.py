from flask import Blueprint, request, jsonify, session, current_app
from src.models.user import db, User
from src.models.ticket import Ticket
from src.models.client import Client
from src.models.service_type import ServiceType
from flask_cors import cross_origin
from datetime import datetime
from src.models.ticket_response import TicketResponse # Movido para o topo

# Importar função de notificação do helpdesk
try:
    from src.routes.helpdesk import criar_notificacao_novo_chamado
    from src.models.helpdesk_models import Chamado as HelpdeskChamado, Usuario as HelpdeskUsuario
except ImportError:
    criar_notificacao_novo_chamado = None
    HelpdeskChamado = None
    HelpdeskUsuario = None

def create_helpdesk_notification(ticket):
    """Cria uma notificação no sistema helpdesk quando um ticket é criado via API"""
    if not (criar_notificacao_novo_chamado and HelpdeskChamado and HelpdeskUsuario):
        return
    
    try:
        # Buscar o usuário no sistema helpdesk
        user = User.query.get(ticket.user_id)
        if not user:
            return
            
        # Criar um objeto chamado temporário para a notificação
        fake_chamado = type('obj', (object,), {
            'id': ticket.id,
            'titulo': ticket.title,
            'prioridade': ticket.priority,
            'usuario': type('obj', (object,), {
                'nome': user.username or user.email
            })()
        })()
        
        # Criar as notificações
        criar_notificacao_novo_chamado(fake_chamado)
        
    except Exception as e:
        print(f"Erro ao criar notificação helpdesk: {e}")

tickets_bp = Blueprint("tickets", __name__)

def require_auth():
    """Decorator para verificar autenticação"""
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    return None

@tickets_bp.route('/tickets', methods=['GET'])
@cross_origin()
def get_tickets():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = session['user_id']
        user_profile = session['profile']
        
        # Administradores e técnicos veem todos os tickets
        if user_profile in ['administrador', 'tecnico']:
            tickets = Ticket.query.all()
        else:
            # Usuários comuns veem apenas seus próprios tickets
            tickets = Ticket.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'tickets': [ticket.to_dict() for ticket in tickets]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tickets_bp.route('/tickets', methods=['POST'])
@cross_origin()
def create_ticket():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        service_type = data.get('service_type')
        priority = data.get('priority', 'media')
        
        if not title or not description or not service_type:
            return jsonify({'error': 'Título, descrição e tipo de serviço são obrigatórios'}), 400
        
        if service_type not in ['consultoria', 'seguranca', 'desenvolvimento']:
            return jsonify({'error': 'Tipo de serviço inválido'}), 400
        
        if priority not in ['baixa', 'media', 'alta']:
            return jsonify({'error': 'Prioridade inválida'}), 400
        
        ticket = Ticket(
            title=title,
            description=description,
            service_type=service_type,
            priority=priority,
            user_id=session['user_id']
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Criar notificações para administradores e técnicos
        try:
            create_helpdesk_notification(ticket)
            
            # Emitir notificação WebSocket em tempo real
            from flask import current_app
            if hasattr(current_app, 'emit_new_ticket_notification'):
                user = User.query.get(ticket.user_id)
                ticket_data = {
                    'id': ticket.id,
                    'titulo': ticket.title,
                    'prioridade': ticket.priority,
                    'usuario': user.username if user else 'Usuário Desconhecido',
                    'created_at': ticket.created_at.isoformat(),
                    'status': ticket.status
                }
                current_app.emit_new_ticket_notification(ticket_data)
                
        except Exception as e:
            print(f"Erro ao criar notificação: {e}")  # Log do erro, mas não bloqueia o chamado
        
        return jsonify({
            'message': 'Chamado criado com sucesso',
            'ticket': ticket.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tickets_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@cross_origin()
def get_ticket_by_id(ticket_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        user_profile = session["profile"]
        user_id = session["user_id"]
        
        # Usuários comuns só podem ver seus próprios tickets
        if user_profile == "usuario" and ticket.user_id != user_id:
            return jsonify({"error": "Sem permissão para ver este chamado"}), 403
        
        return jsonify({"ticket": ticket.to_dict()}), 200
        
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@tickets_bp.route("/tickets/<int:ticket_id>", methods=["PUT"])
@cross_origin()
def update_ticket(ticket_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        user_profile = session['profile']
        user_id = session['user_id']
        
        # Verifica permissões
        if user_profile == 'usuario' and ticket.user_id != user_id:
            return jsonify({'error': 'Sem permissão para editar este chamado'}), 403
        
        data = request.get_json()
        
        # Capturar valores antigos para log
        old_values = {
            'title': ticket.title,
            'description': ticket.description,
            'priority': ticket.priority,
            'status': ticket.status,
            'assigned_to': ticket.assigned_to
        }
        
        # Campos que podem ser atualizados
        if 'title' in data:
            ticket.title = data['title']
        if 'description' in data:
            ticket.description = data['description']
        if 'priority' in data and data['priority'] in ['baixa', 'media', 'alta']:
            ticket.priority = data['priority']
        
        # Apenas administradores e técnicos podem alterar status e atribuição
        if user_profile in ['administrador', 'tecnico']:
            if 'status' in data and data['status'] in ['aberto', 'em_andamento', 'fechado']:
                ticket.status = data['status']
            if 'assigned_to' in data:
                ticket.assigned_to = data['assigned_to']
        
        # Capturar novos valores para log
        new_values = {
            'title': ticket.title,
            'description': ticket.description,
            'priority': ticket.priority,
            'status': ticket.status,
            'assigned_to': ticket.assigned_to
        }
        
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log da atualização do ticket
        from src.utils.activity_logger import activity_logger
        activity_logger.log_update(
            module="tickets",
            entity_type="Ticket",
            entity_id=ticket.id,
            description=f"Atualizou ticket '{ticket.title}' (Status: {ticket.status})",
            old_values=old_values,
            new_values=new_values
        )
        
        return jsonify({
            'message': 'Chamado atualizado com sucesso',
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tickets_bp.route('/tickets/<int:ticket_id>', methods=['DELETE'])
@cross_origin()
def delete_ticket(ticket_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        user_profile = session['profile']
        user_id = session['user_id']
        
        # Apenas administradores ou o próprio usuário podem deletar
        if user_profile != 'administrador' and ticket.user_id != user_id:
            return jsonify({'error': 'Sem permissão para deletar este chamado'}), 403
        
        # Capturar dados para log antes de deletar
        old_values = {
            'title': ticket.title,
            'description': ticket.description,
            'priority': ticket.priority,
            'status': ticket.status,
            'service_type': ticket.service_type,
            'user_id': ticket.user_id,
            'assigned_to': ticket.assigned_to
        }
        
        db.session.delete(ticket)
        db.session.commit()
        
        # Log da deleção do ticket
        from src.utils.activity_logger import activity_logger
        activity_logger.log_delete(
            module="tickets",
            entity_type="Ticket",
            entity_id=ticket_id,
            description=f"Deletou ticket '{old_values['title']}' (Status: {old_values['status']})",
            old_values=old_values
        )
        
        return jsonify({'message': 'Chamado deletado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tickets_bp.route('/tickets/stats', methods=['GET'])
@cross_origin()
def get_ticket_stats():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_profile = session['profile']
        
        if user_profile in ['administrador', 'tecnico']:
            total_tickets = Ticket.query.count()
            open_tickets = Ticket.query.filter_by(status='aberto').count()
            in_progress_tickets = Ticket.query.filter_by(status='em_andamento').count()
            closed_tickets = Ticket.query.filter_by(status='fechado').count()
        else:
            user_id = session['user_id']
            total_tickets = Ticket.query.filter_by(user_id=user_id).count()
            open_tickets = Ticket.query.filter_by(user_id=user_id, status='aberto').count()
            in_progress_tickets = Ticket.query.filter_by(user_id=user_id, status='em_andamento').count()
            closed_tickets = Ticket.query.filter_by(user_id=user_id, status='fechado').count()
        
        return jsonify({
            'stats': {
                'total': total_tickets,
                'aberto': open_tickets,
                'em_andamento': in_progress_tickets,
                'fechado': closed_tickets
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@tickets_bp.route('/tickets/<int:ticket_id>/responses', methods=['GET'])
@cross_origin()
def get_ticket_responses(ticket_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        user_profile = session['profile']
        user_id = session['user_id']
        
        # Verifica permissões
        if user_profile == 'usuario' and ticket.user_id != user_id:
            return jsonify({'error': 'Sem permissão para ver as respostas deste chamado'}), 403
        

        
        # Usuários comuns não veem notas internas
        if user_profile == 'usuario':
            responses = TicketResponse.query.filter_by(ticket_id=ticket_id, is_internal=False).order_by(TicketResponse.created_at).all()
        else:
            responses = TicketResponse.query.filter_by(ticket_id=ticket_id).order_by(TicketResponse.created_at).all()
        
        return jsonify({
            'responses': [response.to_dict() for response in responses]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tickets_bp.route('/tickets/<int:ticket_id>/responses', methods=['POST'])
@cross_origin()
def add_ticket_response(ticket_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        user_profile = session['profile']
        user_id = session['user_id']
        
        # Verifica permissões
        if user_profile == 'usuario' and ticket.user_id != user_id:
            return jsonify({'error': 'Sem permissão para responder este chamado'}), 403
        
        data = request.get_json()
        message = data.get('message')
        is_internal = data.get('is_internal', False)
        
        if not message:
            return jsonify({'error': 'Mensagem é obrigatória'}), 400
        
        # Apenas técnicos e admins podem criar notas internas
        if is_internal and user_profile == 'usuario':
            is_internal = False
        

        
        response = TicketResponse(
            ticket_id=ticket_id,
            user_id=user_id,
            message=message,
            is_internal=is_internal
        )
        
        db.session.add(response)
        
        # Atualiza o status do ticket se necessário
        if user_profile in ['administrador', 'tecnico'] and ticket.status == 'aberto':
            ticket.status = 'em_andamento'
            ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Resposta adicionada com sucesso',
            'response': response.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tickets_bp.route('/tickets/<int:ticket_id>/close', methods=['POST'])
@cross_origin()
def close_ticket(ticket_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        user_profile = session['profile']
        user_id = session['user_id']
        
        # Apenas técnicos e admins podem fechar chamados
        if user_profile not in ['administrador', 'tecnico']:
            return jsonify({'error': 'Sem permissão para fechar chamados'}), 403
        
        data = request.get_json()
        close_message = data.get('message', '')
        
        # Adiciona mensagem de fechamento se fornecida
        if close_message:
    
            response = TicketResponse(
                ticket_id=ticket_id,
                user_id=user_id,
                message=f"Chamado fechado: {close_message}",
                is_internal=False
            )
            db.session.add(response)
        
        ticket.status = 'fechado'
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Chamado fechado com sucesso',
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tickets_bp.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@cross_origin()
def assign_ticket(ticket_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        user_profile = session['profile']
        
        # Apenas técnicos e admins podem atribuir chamados
        if user_profile not in ['administrador', 'tecnico']:
            return jsonify({'error': 'Sem permissão para atribuir chamados'}), 403
        
        data = request.get_json()
        assigned_to = data.get('assigned_to')
        
        if assigned_to:
            # Verifica se o usuário existe e é técnico ou admin
            assigned_user = User.query.get(assigned_to)
            if not assigned_user or assigned_user.profile == 'usuario':
                return jsonify({'error': 'Usuário inválido para atribuição'}), 400
        
        ticket.assigned_to = assigned_to
        ticket.updated_at = datetime.utcnow()
        
        if assigned_to and ticket.status == 'aberto':
            ticket.status = 'em_andamento'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Chamado atribuído com sucesso',
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

