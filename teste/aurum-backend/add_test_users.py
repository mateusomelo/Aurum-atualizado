from src.main import app
from src.models.auth import db, User

with app.app_context():
    # Usuários de teste
    users_data = [
        {"username": "admin.sistema", "password": "admin123", "profile": "administrador"},
        {"username": "joao.silva", "password": "tecnico123", "profile": "tecnico"},
        {"username": "maria.santos", "password": "usuario123", "profile": "usuario"}
    ]

    for user_data in users_data:
        user = User.query.filter_by(username=user_data["username"]).first()
        if not user:
            new_user = User(username=user_data["username"], profile=user_data["profile"])
            new_user.set_password(user_data["password"])
            db.session.add(new_user)
            print(f"Usuário {user_data['username']} adicionado.")
        else:
            print(f"Usuário {user_data['username']} já existe.")
    db.session.commit()


