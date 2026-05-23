from flask import Flask, render_template, request, redirect, session, send_file

import sqlite3
import os

import smtplib

from datetime import datetime

from email.mime.text import MIMEText

app = Flask(__name__)

app.secret_key = "contract_secret_key"


# FILE UPLOAD CONFIG

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# DATABASE INITIALIZATION


def initialize_database():

    connection = sqlite3.connect("contracts.db")

    cursor = connection.cursor()

    cursor.execute("""
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
        """)

    connection.commit()

    connection.close()


initialize_database()


# EMAIL FUNCTION


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

    server.sendmail(sender_email, receiver_email, message.as_string())

    server.quit()


# LOGIN PAGE


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        users = {
            "admin": {"password": "admin123", "role": "Contract Manager"},
            "sales": {"password": "sales123", "role": "Sales Representative"},
            "finance": {"password": "finance123", "role": "Finance Team"},
            "legal": {"password": "legal123", "role": "Legal Team"},
        }

        if username in users and password == users[username]["password"]:

            session["user"] = username

            session["role"] = users[username]["role"]

            return redirect("/")

        else:

            return render_template("login.html", error="Invalid Username or Password")

    return render_template("login.html")


# LOGOUT


@app.route("/logout")
def logout():

    session.pop("user", None)

    session.pop("role", None)

    return redirect("/login")


# HOME PAGE


@app.route("/")
def home():

    if "user" not in session:

        return redirect("/login")

    search_query = request.args.get("search")

    connection = sqlite3.connect("contracts.db")

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
            ("%" + search_query + "%", "%" + search_query + "%"),
        )

    else:

        cursor.execute("SELECT * FROM contracts")

    contracts = cursor.fetchall()

    # RECENT CONTRACTS

    cursor.execute("""
        SELECT * FROM contracts
        ORDER BY id DESC
        LIMIT 5
        """)

    recent_contracts = cursor.fetchall()

    # CONTRACT PROCESSING

    all_contracts = []

    today_date = datetime.today().date()

    expiring_contracts = 0

    for contract in contracts:

        end_date = datetime.strptime(contract[5], "%Y-%m-%d").date()

        days_left = (end_date - today_date).days

        if days_left <= 3 and days_left >= 0:

            expiring_contracts += 1

        all_contracts.append(
            {
                "id": contract[0],
                "title": contract[1],
                "client": contract[2],
                "amount": contract[3],
                "start": contract[4],
                "end": contract[5],
                "status": contract[6],
                "file": contract[7],
                "days_left": days_left,
            }
        )

    # DASHBOARD COUNTS

    cursor.execute("SELECT COUNT(*) FROM contracts")

    total_contracts = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM contracts
        WHERE contract_status='Approved'
        """)

    approved_contracts = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM contracts
        WHERE contract_status='Pending'
        """)

    pending_contracts = cursor.fetchone()[0]

    # TOTAL REVENUE

    cursor.execute("""
        SELECT SUM(contract_amount)
        FROM contracts
        """)

    total_revenue = cursor.fetchone()[0]

    if total_revenue is None:

        total_revenue = 0

    # ACTIVE CONTRACTS

    active_contracts = 0

    for item in all_contracts:

        if item["days_left"] > 0:

            active_contracts += 1

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


# ADD CONTRACT


@app.route("/add_contract", methods=["POST"])
def add_contract():

    title = request.form["title"]

    client = request.form["client"]

    amount = request.form["amount"]

    start = request.form["start"]

    end = request.form["end"]

    status = request.form["status"]

    uploaded_file = request.files["contract_file"]

    filename = uploaded_file.filename

    uploaded_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    connection = sqlite3.connect("contracts.db")

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
        (title, client, amount, start, end, status, filename),
    )

    connection.commit()

    connection.close()

    # EMAIL NOTIFICATION

    # Uncomment after adding real gmail credentials

    # send_email_notification(title)

    return redirect("/")


# DELETE CONTRACT


@app.route("/delete_contract/<int:id>")
def delete_contract(id):

    connection = sqlite3.connect("contracts.db")

    cursor = connection.cursor()

    cursor.execute("DELETE FROM contracts WHERE id = ?", (id,))

    connection.commit()

    connection.close()

    return redirect("/")


# CONTRACT DETAILS PAGE


@app.route("/contract/<int:id>")
def contract_details(id):

    if "user" not in session:

        return redirect("/login")

    connection = sqlite3.connect("contracts.db")

    cursor = connection.cursor()

    cursor.execute("SELECT * FROM contracts WHERE id = ?", (id,))

    contract = cursor.fetchone()

    connection.close()

    summary = f"""

    This contract is created for
    {contract[2]}.

    The total contract amount is
    ₹ {contract[3]}.

    Current contract status is
    {contract[6]}.

    The contract duration is from
    {contract[4]}
    to
    {contract[5]}.

    """

    return render_template(
        "contract_details.html",
        contract=contract,
        role=session.get("role"),
        summary=summary,
    )


# # DOWNLOAD REPORT


# @app.route("/download_report")
# def download_report():

#     connection = sqlite3.connect("contracts.db")

#     query = """

#     SELECT

#         contract_title,
#         client_name,
#         contract_amount,
#         start_date,
#         end_date,
#         contract_status

#     FROM contracts

#     """

#     dataframe = pd.read_sql_query(query, connection)

#     report_file = "contract_report.xlsx"

#     dataframe.to_excel(report_file, index=False)

#     connection.close()

#     return send_file(report_file, as_attachment=True)


# RUN APP

if __name__ == "__main__":

    app.run(debug=True)
