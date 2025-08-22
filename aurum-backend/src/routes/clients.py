from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.client import Client

clients_bp = Blueprint('clients', __name__)

def check_admin_or_tech_permission():
    """Verifica se o usuário logado é administrador ou técnico"""
    if 'user_id' not in session:
        return False
    
    user = User.query.get(session['user_id'])
    return user and user.profile in ['administrador', 'tecnico']

@clients_bp.route('/clients', methods=['GET'])
def get_clients():
    """Lista todos os clientes"""
    try:
        clients = Client.query.filter_by(active=True).all()
        return jsonify([client.to_dict() for client in clients]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/clients', methods=['POST'])
def create_client():
    """Cria um novo cliente"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('name'):
            return jsonify({'error': 'Nome é obrigatório'}), 400
        
        if not data.get('email'):
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        # Verifica se o email já existe
        existing_client = Client.query.filter_by(email=data['email']).first()
        if existing_client:
            return jsonify({'error': 'Email já cadastrado'}), 400
        
        # Cria o novo cliente
        new_client = Client(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone'),
            company=data.get('company'),
            address=data.get('address')
        )
        
        db.session.add(new_client)
        db.session.commit()
        
        return jsonify(new_client.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    """Atualiza um cliente (para administradores e técnicos)"""
    if not check_admin_or_tech_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores e técnicos podem acessar esta funcionalidade.'}), 403
    
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        data = request.get_json()
        
        # Atualiza os campos se fornecidos
        if 'name' in data:
            client.name = data['name']
        
        if 'email' in data:
            # Verifica se o novo email já existe (exceto para o próprio cliente)
            existing_client = Client.query.filter(Client.email == data['email'], Client.id != client_id).first()
            if existing_client:
                return jsonify({'error': 'Email já cadastrado'}), 400
            client.email = data['email']
        
        if 'phone' in data:
            client.phone = data['phone']
        
        if 'company' in data:
            client.company = data['company']
        
        if 'address' in data:
            client.address = data['address']
        
        if 'active' in data:
            client.active = data['active']
        
        db.session.commit()
        return jsonify(client.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    """Exclui um cliente (soft delete - marca como inativo)"""
    if not check_admin_or_tech_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores e técnicos podem acessar esta funcionalidade.'}), 403
    
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        # Soft delete - marca como inativo
        client.active = False
        db.session.commit()
        
        return jsonify({'message': 'Cliente excluído com sucesso'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """Obtém um cliente específico (para administradores e técnicos)"""
    if not check_admin_or_tech_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores e técnicos podem acessar esta funcionalidade.'}), 403
    
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        return jsonify(client.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

