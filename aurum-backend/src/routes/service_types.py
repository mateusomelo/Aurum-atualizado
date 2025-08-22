from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.service_type import ServiceType

service_types_bp = Blueprint('service_types', __name__)

def check_admin_permission():
    """Verifica se o usuário logado é administrador"""
    if 'user_id' not in session:
        return False
    
    user = User.query.get(session['user_id'])
    return user and user.profile == 'administrador'

@service_types_bp.route('/service-types', methods=['GET'])
def get_service_types():
    """Lista todos os tipos de serviço ativos"""
    try:
        service_types = ServiceType.query.filter_by(active=True).all()
        return jsonify([service_type.to_dict() for service_type in service_types]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@service_types_bp.route('/service-types', methods=['POST'])
def create_service_type():
    """Cria um novo tipo de serviço"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('name'):
            return jsonify({'error': 'Nome é obrigatório'}), 400
        
        # Verifica se o nome já existe
        existing_service_type = ServiceType.query.filter_by(name=data['name']).first()
        if existing_service_type:
            return jsonify({'error': 'Tipo de serviço já existe'}), 400
        
        # Cria o novo tipo de serviço
        new_service_type = ServiceType(
            name=data['name'],
            description=data.get('description', '')
        )
        
        db.session.add(new_service_type)
        db.session.commit()
        
        return jsonify(new_service_type.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@service_types_bp.route('/service-types/<int:service_type_id>', methods=['PUT'])
def update_service_type(service_type_id):
    """Atualiza um tipo de serviço (apenas para administradores)"""
    if not check_admin_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.'}), 403
    
    try:
        service_type = ServiceType.query.get(service_type_id)
        if not service_type:
            return jsonify({'error': 'Tipo de serviço não encontrado'}), 404
        
        data = request.get_json()
        
        # Atualiza os campos se fornecidos
        if 'name' in data:
            # Verifica se o novo nome já existe (exceto para o próprio tipo de serviço)
            existing_service_type = ServiceType.query.filter(ServiceType.name == data['name'], ServiceType.id != service_type_id).first()
            if existing_service_type:
                return jsonify({'error': 'Tipo de serviço já existe'}), 400
            service_type.name = data['name']
        
        if 'description' in data:
            service_type.description = data['description']
        
        if 'active' in data:
            service_type.active = data['active']
        
        db.session.commit()
        return jsonify(service_type.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@service_types_bp.route('/service-types/<int:service_type_id>', methods=['DELETE'])
def delete_service_type(service_type_id):
    """Exclui um tipo de serviço (soft delete - marca como inativo)"""
    if not check_admin_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.'}), 403
    
    try:
        service_type = ServiceType.query.get(service_type_id)
        if not service_type:
            return jsonify({'error': 'Tipo de serviço não encontrado'}), 404
        
        # Soft delete - marca como inativo
        service_type.active = False
        db.session.commit()
        
        return jsonify({'message': 'Tipo de serviço excluído com sucesso'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@service_types_bp.route('/service-types/<int:service_type_id>', methods=['GET'])
def get_service_type(service_type_id):
    """Obtém um tipo de serviço específico"""
    try:
        service_type = ServiceType.query.get(service_type_id)
        if not service_type:
            return jsonify({'error': 'Tipo de serviço não encontrado'}), 404
        
        return jsonify(service_type.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

