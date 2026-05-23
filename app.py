from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import os
import smtplib

from datetime import datetime

from email.mime.text import MIMEText

from werkzeug.utils import secure_filename


app = Flask(__name__)

app.secret_key = "contract_secret_key"


# =========================
# FILE UPLOAD CONFIG
# =========================

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================
# DATABASE CONFIG
# =========================

DATABASE = "contracts.db"


def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# =========================
# DATABASE INITIALIZATION
# =========================

def initialize_database():

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """

        CREATE TABLE IF NOT EXISTS contracts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            contract_title TEXT,

            client_name TEXT,

            contract_amount INTEGER,

            start_date TEXT,

            end_date TEXT,

            contract_status TEXT,

            contract_file TEXT

        )

        """
    )

    connection.commit()

    connection.close()


initialize_database()


# =========================
# EMAIL FUNCTION
# =========================

def send_email_notification(contract_title):

    sender_email = "yourgmail@gmail.com"

    sender_password = "your_app_password"

    receiver_email = "receiver@gmail.com"

    subject = "New Contract Added"

    body = f"""

    A new contract has been added.

    Contract Title:
    {contract_title}

    """

    message = MIMEText(body)

    message["Subject"] = subject

    message["From"] = sender_email

    message["To"] = receiver_email

    server = smtplib.SMTP("smtp.gmail.com", 587)

    server.starttls()

    server.login(sender_email, sender_password)

    server.sendmail(

        sender_email,

        receiver_email,

        message.as_string()

    )

    server.quit()


# =========================
# LOGIN PAGE
# =========================

@app.route("/login", methods=["GET", "POST"])

def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        users = {

            "admin": {

                "password": "admin123",

                "role": "Contract Manager"

            },

            "sales": {

                "password": "sales123",

                "role": "Sales Representative"

            },

            "finance": {

                "password": "finance123",

                "role": "Finance Team"

            },

            "legal": {

                "password": "legal123",

                "role": "Legal Team"

            },

        }

        if username in users and password == users[username]["password"]:

            session["user"] = username

            session["role"] = users[username]["role"]

            return redirect("/")

        else:

            return render_template(

                "login.html",

                error="Invalid Username or Password"

            )

    return render_template("login.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")

def logout():

    session.clear()

    return redirect("/login")


# =========================
# HOME PAGE
# =========================

@app.route("/")

def home():

    if "user" not in session:

        return redirect("/login")

    search_query = request.args.get("search")

    connection = get_db_connection()

    cursor = connection.cursor()

    # SEARCH

    if search_query:

        cursor.execute(
            """

            SELECT * FROM contracts

            WHERE
            contract_title LIKE ?
            OR client_name LIKE ?

            """,

            (

                "%" + search_query + "%",

                "%" + search_query + "%"

            ),

        )

    else:

        cursor.execute(

            "SELECT * FROM contracts"

        )

    contracts = cursor.fetchall()

    # RECENT CONTRACTS

    cursor.execute(
        """

        SELECT * FROM contracts

        ORDER BY id DESC

        LIMIT 5

        """
    )

    recent_contracts = cursor.fetchall()

    # CONTRACT PROCESSING

    all_contracts = []

    today_date = datetime.today().date()

    expiring_contracts = 0

    for contract in contracts:

        try:

            end_date = datetime.strptime(

                contract["end_date"],

                "%Y-%m-%d"

            ).date()

            days_left = (

                end_date - today_date

            ).days

        except:

            days_left = 0

        if days_left <= 3 and days_left >= 0:

            expiring_contracts += 1

        all_contracts.append(

            {

                "id": contract["id"],

                "title": contract["contract_title"],

                "client": contract["client_name"],

                "amount": contract["contract_amount"],

                "start": contract["start_date"],

                "end": contract["end_date"],

                "status": contract["contract_status"],

                "file": contract["contract_file"],

                "days_left": days_left,

            }

        )

    # DASHBOARD COUNTS

    total_contracts = len(all_contracts)

    approved_contracts = len(

        [

            c for c in all_contracts

            if c["status"].lower() == "approved"

        ]

    )

    pending_contracts = len(

        [

            c for c in all_contracts

            if c["status"].lower() == "pending"

        ]

    )

    total_revenue = sum(

        [

            int(c["amount"])

            for c in all_contracts

        ]

    )

    active_contracts = len(

        [

            c for c in all_contracts

            if c["days_left"] > 0

        ]

    )

    connection.close()

    return render_template(

        "index.html",

        contracts=all_contracts,

        total=total_contracts,

        approved=approved_contracts,

        pending=pending_contracts,

        role=session.get("role"),

        recent=recent_contracts,

        alerts=expiring_contracts,

        revenue=total_revenue,

        active=active_contracts,

    )


# =========================
# ADD CONTRACT
# =========================

@app.route("/add_contract", methods=["POST"])

def add_contract():

    title = request.form["title"]

    client = request.form["client"]

    amount = request.form["amount"]

    start = request.form["start"]

    end = request.form["end"]

    status = request.form["status"]

    uploaded_file = request.files["contract_file"]

    filename = ""

    if uploaded_file:

        filename = secure_filename(

            uploaded_file.filename

        )

        uploaded_file.save(

            os.path.join(

                app.config["UPLOAD_FOLDER"],

                filename

            )

        )

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """

        INSERT INTO contracts (

            contract_title,

            client_name,

            contract_amount,

            start_date,

            end_date,

            contract_status,

            contract_file

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)

        """,

        (

            title,

            client,

            amount,

            start,

            end,

            status,

            filename,

        ),
    )

    connection.commit()

    connection.close()

    return redirect("/")


# =========================
# DELETE CONTRACT
# =========================

@app.route("/delete_contract/<int:id>")

def delete_contract(id):

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(

        "DELETE FROM contracts WHERE id = ?",

        (id,)

    )

    connection.commit()

    connection.close()

    return redirect("/")


# =========================
# CONTRACT DETAILS PAGE
# =========================

@app.route("/contract/<int:id>")

def contract_details(id):

    if "user" not in session:

        return redirect("/login")

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(

        "SELECT * FROM contracts WHERE id = ?",

        (id,)

    )

    contract = cursor.fetchone()

    connection.close()

    summary = f"""

    This contract is created for
    {contract['client_name']}.

    The total contract amount is
    ₹ {contract['contract_amount']}.

    Current contract status is
    {contract['contract_status']}.

    The contract duration is from
    {contract['start_date']}
    to
    {contract['end_date']}.

    """

    return render_template(

        "contract_details.html",

        contract=contract,

        role=session.get("role"),

        summary=summary,

    )


# =========================
# DOWNLOAD CONTRACT FILE
# =========================

@app.route("/download/<filename>")

def download_file(filename):

    return send_file(

        os.path.join(

            app.config["UPLOAD_FOLDER"],

            filename

        ),

        as_attachment=True

    )


# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    app.run(debug=True)