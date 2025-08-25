from flask import Blueprint, request, jsonify, session
from src.models.user import db
from src.models.contact import Contact

contact_bp = Blueprint('contact_bp', __name__)

@contact_bp.route('/contacts', methods=['POST'])
def create_contact():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    subject = data.get('subject')
    message = data.get('message')

    if not all([name, email, phone, subject, message]):
        return jsonify({'message': 'Missing data'}), 400

    new_contact = Contact(name=name, email=email, phone=phone, subject=subject, message=message)
    db.session.add(new_contact)
    db.session.commit()

    return jsonify({'message': 'Contact created successfully', 'contact': new_contact.id}), 201

@contact_bp.route('/contacts', methods=['GET'])
def get_contacts():
    # Verificar se o usuário está logado e é administrador
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    if session.get('profile') != 'administrador':
        return jsonify({'error': 'Acesso negado. Apenas administradores podem ver os contatos.'}), 403
    
    contacts = Contact.query.all()
    output = []
    for contact in contacts:
        output.append({
            'id': contact.id,
            'name': contact.name,
            'email': contact.email,
            'phone': contact.phone,
            'subject': contact.subject,
            'message': contact.message,
            'created_at': contact.created_at.isoformat()
        })
    return jsonify({'contacts': output}), 200

