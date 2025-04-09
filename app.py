from flask import Flask, render_template, request, redirect, session, url_for
from utils.instagram_client import InstagramBot
from utils.logger import log

app = Flask(__name__)
app.secret_key = 'c120e81ecdbe602ad062a3d87630cb516e8cc37229191b67a20411632fad7eee'

client = InstagramBot()

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            success, requires_manual = client.try_login(username, password)
            session["username"] = username
            session["password"] = password
            if requires_manual:
                return redirect(url_for("manual_unsecure"))
            if success:
                return redirect(url_for("dashboard"))
        except Exception as e:
            log(f"❌ Login failed: {e}")
            return render_template("index.html", error=str(e))

    return render_template("index.html")


@app.route("/manual-unsecure", methods=["GET", "POST"])
def manual_unsecure():
    if request.method == "POST":
        username = session.get("username")
        password = session.get("password")
        try:
            success, requires_manual = client.try_login(username, password)
            if success:
                return redirect(url_for("dashboard"))
            else:
                return render_template("manual_unsecure.html", error="Still secured. Try again.")
        except Exception as e:
            return render_template("manual_unsecure.html", error=str(e))
    return render_template("manual_unsecure.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        target_user = request.form["target_user"]
        mode = request.form["mode"]
        message = request.form["message"]
        limit = int(request.form["limit"])
        delay = float(request.form["delay"])

        try:
            users = client.get_users(target_user, mode, limit)
            client.send_messages(users, message, delay)
            return render_template("dashboard.html", logs=client.logs)
        except Exception as e:
            log(f"❌ Error: {e}")
            return render_template("dashboard.html", logs=client.logs, error=str(e))

    return render_template("dashboard.html", logs=client.logs)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
