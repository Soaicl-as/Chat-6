from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from utils.instagram_client import InstagramBot
from utils.logger import Logger
import os
import time
from functools import wraps

app = Flask(__name__)
# Use environment variable for secret key in production
app.secret_key = os.environ.get('SECRET_KEY', 'c120e81ecdbe602ad062a3d87630cb516e8cc37229191b67a20411632fad7eee')

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800

logger = Logger()
client = None

def log(message):
    logger.log(message)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in and session is not expired
        if 'username' not in session or 'last_activity' not in session:
            return redirect(url_for('login'))
        
        # Check if session has expired
        if time.time() - session['last_activity'] > SESSION_TIMEOUT:
            session.clear()
            return redirect(url_for('login', error="Session expired. Please log in again."))
        
        # Update last activity time
        session['last_activity'] = time.time()
        
        # Check if client is ready
        global client
        if not client or not client._ready:
            return redirect(url_for('login'))
            
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET", "POST"])
def login():
    global client
    
    # Clear any existing session
    if 'username' in session and request.method == "GET":
        session.clear()
        client = None
    
    error = request.args.get('error')
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            # Initialize new client
            client = InstagramBot(logger)
            result = client.try_login(username, password)
            
            # Store session data
            session["username"] = username
            session["password"] = password
            session["last_activity"] = time.time()
            
            if result == "2FA_REQUIRED":
                log(f"🔒 2FA required for {username}")
                return redirect(url_for("manual_unsecure"))
            elif result == "LOGIN_SUCCESS":
                log(f"✅ Successfully logged in as {username}")
                return redirect(url_for("dashboard"))
            else:
                log(f"❌ Login failed: {result}")
                client = None
                return render_template("index.html", error=result)
        except Exception as e:
            log(f"❌ Login failed: {e}")
            client = None
            return render_template("index.html", error=str(e))

    return render_template("index.html", error=error)


@app.route("/manual-unsecure", methods=["GET", "POST"])
def manual_unsecure():
    global client
    
    if "username" not in session or "password" not in session or not client:
        return redirect(url_for("login"))
        
    if request.method == "POST":
        try:
            result = client.continue_login()
            if result == "LOGIN_SUCCESS":
                log(f"✅ Successfully logged in as {session['username']}")
                session["last_activity"] = time.time()
                return redirect(url_for("dashboard"))
            elif result == "STILL_WAITING_APPROVAL":
                log(f"⚠️ Still waiting for approval in Instagram app")
                return render_template("manual_unsecure.html", error="Still waiting for approval. Please check your Instagram app or email and approve the login.")
            else:
                log(f"❌ Login still failed: {result}")
                return render_template("manual_unsecure.html", error=f"Login failed: {result}")
        except Exception as e:
            log(f"❌ Error during login: {e}")
            return render_template("manual_unsecure.html", error=str(e))
    
    # On GET request, ensure we're actively triggering the challenge
    try:
        # Explicitly send a challenge request when the page loads
        client.challenge_send()
        log(f"🔒 Sent verification request to Instagram for {session['username']}")
    except Exception as e:
        # Log the error but still show the page
        log(f"⚠️ Challenge trigger error: {e}")
        
    return render_template("manual_unsecure.html")


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    global client
    
    if request.method == "POST":
        target_user = request.form["target_user"]
        mode = request.form["mode"]
        message = request.form["message"]
        limit = int(request.form["limit"])
        delay = float(request.form["delay"])
        
        # Add some basic validation
        if limit > 100:
            log(f"⚠️ Limit reduced from {limit} to 100 to avoid rate limiting")
            limit = 100
            
        if delay < 1.0:
            log(f"⚠️ Delay increased from {delay} to 1.0s to avoid rate limiting")
            delay = 1.0

        try:
            log(f"🔍 Getting {mode} for {target_user}...")
            if mode == "followers":
                users = client.get_followers(target_user, limit)
            else:
                users = client.get_following(target_user, limit)
                
            log(f"✅ Found {len(users)} users")
            
            if len(users) == 0:
                return render_template("dashboard.html", logs=logger.get_logs(), 
                                      error=f"No {mode} found for {target_user}")
            
            log(f"💬 Sending messages with {delay}s delay...")
            count = 0
            errors = 0
            
            for user_id, user_info in users.items():
                try:
                    client.send_dm(user_info, message)
                    log(f"✅ Message sent to {user_info.username}")
                    count += 1
                    time.sleep(delay)  # Move delay here for better control
                except Exception as e:
                    log(f"❌ Error sending to {user_info.username}: {e}")
                    errors += 1
                    
                    # Break if too many errors to avoid getting blocked
                    if errors > 5:
                        log("⚠️ Too many errors, stopping to avoid account restrictions")
                        break
                
            log(f"✅ Successfully sent {count} messages, {errors} failed")
            return render_template("dashboard.html", logs=logger.get_logs(), 
                                  success=f"Sent {count} messages")
        except Exception as e:
            log(f"❌ Error: {e}")
            return render_template("dashboard.html", logs=logger.get_logs(), error=str(e))

    return render_template("dashboard.html", logs=logger.get_logs())


@app.route("/logs", methods=["GET"])
@login_required
def get_logs():
    return jsonify({"logs": logger.get_logs()})


@app.route("/logout")
def logout():
    global client
    
    # Clear session
    session.clear()
    
    # Reset client
    if client:
        try:
            client.logout()
        except:
            pass
    client = None
    
    return redirect(url_for("login"))


@app.route("/status")
@login_required
def status():
    """API endpoint to check if logged in user is still valid"""
    try:
        # Try to do a simple operation to verify the session is still valid
        me = client.get_me()
        return jsonify({
            "status": "ok",
            "username": session.get("username"),
            "user_id": me.pk if me else None
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 401


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    log(f"Server error: {str(e)}")
    return render_template('error.html', error=str(e)), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
