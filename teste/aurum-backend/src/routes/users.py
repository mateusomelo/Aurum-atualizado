from flask import Blueprint, request, jsonify, session
from src.models.user import db, User

users_bp = Blueprint('users', __name__)

def check_admin_permission():
    """Verifica se o usuário logado é administrador"""
    if 'user_id' not in session:
        return False
    
    user = User.query.get(session['user_id'])
    return user and user.profile == 'administrador'

@users_bp.route('/users', methods=['GET'])
def get_users():
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route("/users", methods=["POST"])
def create_user():
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('username'):
            return jsonify({'error': 'Nome de usuário é obrigatório'}), 400
        
        if not data.get('password'):
            return jsonify({'error': 'Senha é obrigatória'}), 400
        
        if not data.get('profile') or data.get('profile') not in ['administrador', 'tecnico', 'usuario']:
            return jsonify({'error': 'Perfil deve ser: administrador, tecnico ou usuario'}), 400
        
        # Verifica se o usuário já existe
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'error': 'Nome de usuário já existe'}), 400
        
        # Cria o novo usuário
        new_user = User(
            username=data["username"],
            profile=data["profile"]
        )
        new_user.set_password(data["password"])
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify(new_user.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Atualiza um usuário (apenas para administradores)"""
    if not check_admin_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        # Atualiza os campos se fornecidos
        if 'username' in data:
            # Verifica se o novo username já existe (exceto para o próprio usuário)
            existing_user = User.query.filter(User.username == data['username'], User.id != user_id).first()
            if existing_user:
                return jsonify({'error': 'Nome de usuário já existe'}), 400
            user.username = data['username']
        
        if 'profile' in data:
            if data['profile'] not in ['administrador', 'tecnico', 'usuario']:
                return jsonify({'error': 'Perfil deve ser: administrador, tecnico ou usuario'}), 400
            user.profile = data['profile']
        
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        db.session.commit()
        return jsonify(user.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Exclui um usuário (apenas para administradores)"""
    if not check_admin_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Não permite excluir o próprio usuário
        if user.id == session['user_id']:
            return jsonify({'error': 'Não é possível excluir seu próprio usuário'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'Usuário excluído com sucesso'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Obtém um usuário específico (apenas para administradores)"""
    if not check_admin_permission():
        return jsonify({'error': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify(user.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

