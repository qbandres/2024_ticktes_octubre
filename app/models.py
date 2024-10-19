from app import db
from datetime import datetime

class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    estatus = db.Column(db.String(10), default='creado')
    stand_1 = db.Column(db.String(10), default='pendiente')
    stand_2 = db.Column(db.String(10), default='pendiente')
    stand_3 = db.Column(db.String(10), default='pendiente')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_closed = db.Column(db.DateTime, nullable=True)

    def close_ticket(self):
        self.estatus = 'cerrado'
        self.date_closed = datetime.utcnow()
