from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    investments = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(10))
    amount = db.Column(db.Float)
    description = db.Column(db.String(200))

def send_email(to, subject, body):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = "your_email@gmail.com"
        msg['To'] = to

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login("your_email@gmail.com", "your_password")
            smtp.send_message(msg)
    except Exception as e:
        print("Email error:", e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        details = request.form['details']
        password = generate_password_hash(request.form['password'])
        user = User(email=email, name=name, details=details, password=password)
        db.session.add(user)
        db.session.commit()
        send_email(email, "Welcome to Perfect Vault", "Thanks for registering, " + name)
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/deposit', methods=['POST'])
def deposit():
    user = User.query.get(session['user_id'])
    amount = float(request.form['amount'])
    description = request.form.get('description', '')
    user.balance += amount
    db.session.add(Transaction(user_id=user.id, type='Deposit', amount=amount, description=description))
    db.session.commit()
    send_email(user.email, "Deposit Received", f"You deposited ${amount:.2f}.")
    return redirect('/dashboard')

@app.route('/withdraw', methods=['POST'])
def withdraw():
    user = User.query.get(session['user_id'])
    amount = float(request.form['amount'])
    description = request.form.get('description', '')
    if user.balance >= amount:
        user.balance -= amount
        db.session.add(Transaction(user_id=user.id, type='Withdraw', amount=amount, description=description))
        db.session.commit()
        send_email(user.email, "Withdrawal Made", f"You withdrew ${amount:.2f}.")
    return redirect('/dashboard')

@app.route('/invest', methods=['POST'])
def invest():
    user = User.query.get(session['user_id'])
    amount = float(request.form['amount'])
    if user.balance >= amount:
        user.balance -= amount
        user.investments += amount
        db.session.add(Transaction(user_id=user.id, type='Invest', amount=amount, description='Investment'))
        db.session.commit()
        send_email(user.email, "Investment Made", f"You invested ${amount:.2f}.")
    return redirect('/dashboard')

@app.route('/export-transactions')
def export_transactions():
    user = User.query.get(session['user_id'])
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    filepath = '/mnt/data/transactions.csv'
    with open(filepath, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Type', 'Amount', 'Description'])
        for t in transactions:
            writer.writerow([t.type, t.amount, t.description])
    return send_file(filepath, as_attachment=True)

@app.route('/admin')
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
