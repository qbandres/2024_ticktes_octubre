# Importaciones necesarias para la aplicación Flask
from flask import Flask, render_template, request, redirect, url_for  # Importaciones de Flask para crear rutas y manejar plantillas HTML
from flask_socketio import SocketIO  # Importación de SocketIO para manejar la comunicación en tiempo real
from flask_sqlalchemy import SQLAlchemy  # Importación de SQLAlchemy para interactuar con la base de datos
from datetime import datetime  # Importación de datetime para manejar fechas y horas

# Configuración e inicialización de la aplicación Flask
app = Flask(__name__, template_folder='templates')  # Creación de la aplicación Flask y especificación de la carpeta de templates

# Configuración de la base de datos PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:20011074@localhost/tickets_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desactiva el seguimiento de modificaciones para mejorar el rendimiento

# Inicialización de las extensiones
db = SQLAlchemy(app)  # Inicialización de SQLAlchemy con la aplicación Flask
socketio = SocketIO(app)  # Inicialización de SocketIO para habilitar eventos en tiempo real

# Definición del modelo de la base de datos para los tickets
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Columna de ID del ticket, clave primaria
    estatus = db.Column(db.String(20), default='creado')  # Estado del ticket, inicializado como "creado"
    stand_1 = db.Column(db.String(20), default='pendiente')  # Estado en el stand 1, inicializado como "pendiente"
    stand_2 = db.Column(db.String(20), default='pendiente')  # Estado en el stand 2, inicializado como "pendiente"
    stand_3 = db.Column(db.String(20), default='pendiente')  # Estado en el stand 3, inicializado como "pendiente"
    date_created = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha y hora de creación del ticket
    date_closed = db.Column(db.DateTime, nullable=True)  # Fecha y hora de cierre del ticket, inicialmente nula

# Ruta raíz de la aplicación, redirige a la vista del administrador
@app.route('/')
def index():
    return redirect(url_for('admin_view'))  # Redirige a la función admin_view

# Vista del administrador, muestra todos los tickets ordenados
@app.route('/admin')
def admin_view():
    # Ordenar por el estado 'creado' primero y luego por la fecha de creación
    tickets = Ticket.query.order_by(Ticket.estatus.desc(), Ticket.date_created).all()
    return render_template('admin.html', tickets=tickets)  # Muestra la plantilla admin.html con la lista de tickets

# Ruta para crear un nuevo ticket
@app.route('/admin/create', methods=['POST'])
def create_ticket():
    new_ticket = Ticket()  # Crea una nueva instancia de Ticket
    db.session.add(new_ticket)  # Añade el nuevo ticket a la sesión de la base de datos
    db.session.commit()  # Guarda los cambios en la base de datos

    # Emite un evento para notificar que se ha creado un nuevo ticket
    socketio.emit('ticket_update', {'action': 'created', 'ticket_id': new_ticket.id})
    
    return redirect(url_for('admin_view'))  # Redirige a la vista del administrador

# Ruta para cerrar un ticket por parte del administrador
@app.route('/admin/close/<int:ticket_id>')
def close_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)  # Recupera el ticket por ID
    if ticket:
        ticket.estatus = 'cerrado'  # Cambia el estado del ticket a "cerrado"
        ticket.stand_1 = 'atendido'  # Marca el ticket como atendido en el stand 1
        ticket.stand_2 = 'atendido'  # Marca el ticket como atendido en el stand 2
        ticket.stand_3 = 'atendido'  # Marca el ticket como atendido en el stand 3
        # Obtener la fecha y hora local del sistema
        ticket.date_closed = datetime.now()  # Usa la hora local del sistema
        db.session.commit()  # Guarda los cambios en la base de datos

        # Emite un evento para notificar que el ticket ha sido cerrado
        socketio.emit('ticket_update', {'action': 'closed', 'ticket_id': ticket.id})
    
    return redirect(url_for('admin_view'))  # Redirige a la vista del administrador

# Función para verificar y cerrar automáticamente un ticket
def check_and_close_ticket(ticket):
    # Verifica si todos los stands están atendidos
    if ticket.stand_1 == 'atendido' and ticket.stand_2 == 'atendido' and ticket.stand_3 == 'atendido':
        ticket.estatus = 'cerrado'
        ticket.date_closed = datetime.now()  # Registra la fecha y hora local del sistema
        db.session.commit()  # Guarda los cambios en la base de datos

        # Emite un evento para notificar que el ticket ha sido cerrado
        socketio.emit('ticket_update', {'action': 'closed', 'ticket_id': ticket.id})

# Vista del visualizador, muestra los tickets en estado "creado"
@app.route('/visualizador')
def visualizador_view():
    tickets = Ticket.query.filter(Ticket.estatus == 'creado').all()  # Recupera todos los tickets con estado "creado"
    return render_template('visualizador.html', tickets=tickets)  # Muestra la plantilla visualizador.html con la lista de tickets

# Vista de los expositores, muestra los tickets pendientes o en proceso para el stand correspondiente
@app.route('/expositor/<int:stand_number>')
def expositor_view(stand_number):
    # Identifica la columna del stand correspondiente
    stand_col = f'stand_{stand_number}'
    # Recupera los tickets en estado "pendiente" o "en proceso" para el stand correspondiente
    tickets = Ticket.query.filter(
        (getattr(Ticket, stand_col).in_(['pendiente', 'en proceso']))
    ).all()
    return render_template(f'expositor_{stand_number}.html', tickets=tickets)  # Muestra la plantilla del expositor correspondiente

# Ruta para llamar a un ticket en un stand
@app.route('/expositor/<int:stand_number>/call/<int:ticket_id>', methods=['POST'])
def call_ticket(stand_number, ticket_id):
    ticket = Ticket.query.get(ticket_id)  # Recupera el ticket por ID
    stand_col = f'stand_{stand_number}'  # Identifica la columna del stand correspondiente
    if ticket and getattr(ticket, stand_col) == 'pendiente':
        # Cambia el estado del ticket a "en proceso" para el stand actual
        setattr(ticket, stand_col, 'en proceso')
        # Cambia el estado de los otros stands a "llamado" si no han sido atendidos
        for i in range(1, 4):
            if i != stand_number and getattr(ticket, f'stand_{i}') != 'atendido':
                setattr(ticket, f'stand_{i}', 'llamado')
        db.session.commit()  # Guarda los cambios en la base de datos

        # Emite un evento para notificar que un ticket ha sido llamado en un stand
        socketio.emit('ticket_update', {'action': 'called', 'ticket_id': ticket.id, 'stand': stand_number})
    
    return redirect(url_for('expositor_view', stand_number=stand_number))  # Redirige a la vista del expositor correspondiente

# Ruta para cerrar un ticket en un stand específico
@app.route('/expositor/<int:stand_number>/close/<int:ticket_id>', methods=['POST'])
def close_expositor_ticket(stand_number, ticket_id):
    ticket = Ticket.query.get(ticket_id)  # Recupera el ticket por ID
    stand_col = f'stand_{stand_number}'  # Identifica la columna del stand correspondiente
    if ticket and getattr(ticket, stand_col) == 'en proceso':
        # Cambia el estado del ticket a "atendido" en el stand actual
        setattr(ticket, stand_col, 'atendido')
        # Cambia el estado de los otros stands a "pendiente" si no han sido atendidos
        for i in range(1, 4):
            if i != stand_number and getattr(ticket, f'stand_{i}') != 'atendido':
                setattr(ticket, f'stand_{i}', 'pendiente')

        db.session.commit()  # Guarda los cambios en la base de datos

        # Emite un evento para notificar que un ticket ha sido atendido en un stand
        socketio.emit('ticket_update', {'action': 'attended', 'ticket_id': ticket.id, 'stand': stand_number})

        # Verificar si todos los stands están atendidos para cerrar el ticket automáticamente
        check_and_close_ticket(ticket)
    
    return redirect(url_for('expositor_view', stand_number=stand_number))  # Redirige a la vista del expositor correspondiente

# Iniciar la aplicación y el servidor SocketIO
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea las tablas de la base de datos si no existen
    socketio.run(app, debug=True)  # Ejecuta la aplicación en modo debug y habilita SocketIO
