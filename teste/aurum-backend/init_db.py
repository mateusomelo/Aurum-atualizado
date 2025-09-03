from src.main import app
from src.models.auth import db

with app.app_context():
    db.create_all()


