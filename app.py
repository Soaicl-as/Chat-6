from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from utils.instagram_client import InstagramBot
from utils.logger import Logger

app = Flask(__name__)
app.secret_key = 'c120e81ecdbe602ad062a3d87630cb516e8cc37229191b67a20411632fad7eee'

logger = Logger()
client = InstagramBot(logger)

def log(message):
    logger.log(message)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            result = client.try_login(username, password)
            session["username"] = username
            session["password"] = password
            
            if result == "2FA_REQUIRED":
                return redirect(url_for("manual_unsecure"))
            elif result == "LOGIN_SUCCESS":
                return redirect(url_for("dashboard"))
            else:
                log(f"❌ Login failed: {result}")
                return render_template("index.html", error=result)
        except Exception as e:
            log(f"❌ Login failed: {e}")
            return render_template("index.html", error=str(e))

    return render_template("index.html")


@app.route("/manual-unsecure", methods=["GET", "POST"])
def manual_unsecure():
    if request.method == "POST":
        try:
            result = client.continue_login()
            if result == "LOGIN_SUCCESS":
                return redirect(url_for("dashboard"))
            else:
                return render_template("manual_unsecure.html", error="Still secured. Try again.")
        except Exception as e:
            return render_template("manual_unsecure.html", error=str(e))
    return render_template("manual_unsecure.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not client._ready:
        return redirect(url_for("login"))
        
    if request.method == "POST":
        target_user = request.form["target_user"]
        mode = request.form["mode"]
        message = request.form["message"]
        limit = int(request.form["limit"])
        delay = float(request.form["delay"])

        try:
            log(f"🔍 Getting {mode} for {target_user}...")
            if mode == "followers":
                users = client.get_followers(target_user, limit)
            else:
                users = client.get_following(target_user, limit)
                
            log(f"✅ Found {len(users)} users")
            
            log(f"💬 Sending messages with {delay}s delay...")
            count = 0
            for user_id, user_info in users.items():
                try:
                    client.send_dm(user_info, message)
                    log(f"✅ Message sent to {user_info.username}")
                    count += 1
                except Exception as e:
                    log(f"❌ Error sending to {user_info.username}: {e}")
                
            log(f"✅ Successfully sent {count} messages")
            return render_template("dashboard.html", logs=logger.get_logs())
        except Exception as e:
            log(f"❌ Error: {e}")
            return render_template("dashboard.html", logs=logger.get_logs(), error=str(e))

    return render_template("dashboard.html", logs=logger.get_logs())


@app.route("/logs", methods=["GET"])
def get_logs():
    return jsonify({"logs": logger.get_logs()})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
