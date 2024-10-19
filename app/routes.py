from flask import render_template, redirect, url_for, request
from app import app, db, socketio
from app.models import Ticket
from datetime import datetime

@app.route('/')
def index():
    return redirect(url_for('admin_view'))

@app.route('/admin')
def admin_view():
    tickets = Ticket.query.all()
    return render_template('admin.html', tickets=tickets)

@app.route('/admin/create', methods=['POST'])
def create_ticket():
    # Crear un nuevo ticket con los valores iniciales
    new_ticket = Ticket(
        estatus='creado',
        stand_1='pendiente',
        stand_2='pendiente',
        stand_3='pendiente',
        date_created=datetime.utcnow()
    )
    db.session.add(new_ticket)
    db.session.commit()

    # Emitir evento para notificar a todos los clientes que un ticket fue creado
    print(f"Emitiendo evento para ticket {new_ticket.id}")
    socketio.emit('ticket_update', {'action': 'created', 'ticket_id': new_ticket.id}, to='/')

    return redirect(url_for('admin_view'))


@app.route('/admin/close/<int:ticket_id>')
def close_ticket_admin(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        ticket.estatus = 'cerrado'
        ticket.date_closed = datetime.utcnow()
        db.session.commit()

        # Emitir evento para notificar que un ticket fue cerrado
        socketio.emit('ticket_update', {'action': 'closed', 'ticket_id': ticket.id}, to='/')

    return redirect(url_for('admin_view'))

@app.route('/expositor/<int:stand_number>')
def expositor_view(stand_number):
    stand_col = f'stand_{stand_number}'
    tickets = Ticket.query.filter(getattr(Ticket, stand_col) == 'pendiente').all()
    return render_template(f'expositor_{stand_number}.html', tickets=tickets)

@app.route('/visualizador')
def visualizador_view():
    tickets = Ticket.query.filter(Ticket.estatus == 'creado').all()
    return render_template('visualizador.html', tickets=tickets)

@app.route('/expositor/<int:stand_number>/call/<int:ticket_id>')
def call_ticket(stand_number, ticket_id):
    ticket = Ticket.query.get(ticket_id)
    stand_col = f'stand_{stand_number}'
    if ticket:
        setattr(ticket, stand_col, 'en proceso')
        db.session.commit()

        # Emitir evento para notificar que un ticket está en proceso en un stand
        socketio.emit('ticket_update', {'action': 'called', 'ticket_id': ticket.id, 'stand': stand_number}, to='/')

    return redirect(url_for('expositor_view', stand_number=stand_number))

@app.route('/expositor/<int:stand_number>/close/<int:ticket_id>')
def close_expositor_ticket(stand_number, ticket_id):
    ticket = Ticket.query.get(ticket_id)
    stand_col = f'stand_{stand_number}'
    if ticket:
        setattr(ticket, stand_col, 'atendido')
        db.session.commit()

        # Emitir evento para notificar que un ticket fue atendido en un stand
        socketio.emit('ticket_update', {'action': 'attended', 'ticket_id': ticket.id, 'stand': stand_number}, to='/')

    return redirect(url_for('expositor_view', stand_number=stand_number))
