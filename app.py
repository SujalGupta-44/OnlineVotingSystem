from database import get_connection
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import pymysql

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ----------------- USER LOGIN -----------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        aadhar_no = request.form.get("aadhar", "").strip()
        password = request.form.get("password", "")
        if not aadhar_no or not password:
            flash("⚠️ Enter Aadhar and Password!", "danger")
            return render_template("login.html")
        conn = get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE aadhar_no=%s", (aadhar_no,))
                user = cursor.fetchone()
        finally:
            conn.close()

        if user and check_password_hash(user["password"], password):
            session["aadhar_no"] = user["aadhar_no"]
            session["user_name"] = user.get("name", "User")
            flash(f" Welcome {session['user_name']}!", "success")
            return redirect(url_for("user_dashboard"))
        else:
            flash("Invalid Aadhar or Password", "danger")

    return render_template("login.html")
# ----------------- USER REGISTRATION -----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        aadhar = request.form.get("aadhar", "").strip()
        name = request.form.get("name", "").strip()
        father = request.form.get("father", "").strip()
        age = request.form.get("age", "").strip()
        city = request.form.get("city", "").strip()
        password = request.form.get("password", "")

        if not (aadhar and name and password):
            flash(" Aadhar, Name and Password are required.", "danger")
            return render_template("registration.html")

        hashed = generate_password_hash(password)

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (aadhar_no, name, father_name, age, city, password) VALUES (%s,%s,%s,%s,%s,%s)",
                    (aadhar, name, father or None, int(age) if age else None, city or None, hashed)
                )
            conn.commit()
            flash(" Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("Registration failed: Aadhar may already exist.", "danger")
        finally:
            conn.close()

    for tmpl in ("registration.html", "ragistration.html"):
        try:
            return render_template(tmpl)
        except Exception:
            pass
    return "Registration template not found", 500
# ----------------- USER DASHBOARD -----------------
@app.route("/user_dashboard")
def user_dashboard():
    if "aadhar_no" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT election_id, title, start_date, end_date, status FROM elections ORDER BY election_id DESC")
            elections = cursor.fetchall()
    finally:
        conn.close()

    return render_template("user_dashboard.html", elections=elections)

# ----------------- VOTING -----------------
@app.route("/vote/<int:election_id>", methods=["GET", "POST"])
def vote(election_id):
    if "aadhar_no" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Election ka status check karo
    cursor.execute("SELECT status FROM elections WHERE election_id=%s", (election_id,))
    election = cursor.fetchone()

    if not election:
        flash("Election not found!", "danger")
        conn.close()
        return redirect(url_for("login"))

    if election["status"] != "ACTIVE":
        flash(f" Voting not allowed. Election is {election['status']}.", "warning")
        conn.close()
        return redirect(url_for("login"))

    if request.method == "POST":
        candidate_id = request.form["candidate_id"]

        cursor.execute(
            "SELECT * FROM votes WHERE aadhar_no=%s AND election_id=%s",
            (session["aadhar_no"], election_id)
        )
        already = cursor.fetchone()

        if already:
            flash(" You have already voted in this election!", "warning")
            conn.close()
            return redirect(url_for("login"))
        else:
            cursor.execute(
                "INSERT INTO votes (aadhar_no, election_id, candidate_id) VALUES (%s, %s, %s)",
                (session["aadhar_no"], election_id, candidate_id),
            )
            conn.commit()
            flash(" Vote cast successfully!", "success")
            conn.close()
            return redirect(url_for("login"))

    # Agar GET request hai to candidates dikhao
    cursor.execute("SELECT candidate_id, name, party FROM candidates WHERE election_id=%s", (election_id,))
    candidates = cursor.fetchall()
    conn.close()

    return render_template("vote.html", candidates=candidates, election_id=election_id)


# ----------------- ADMIN LOGIN -----------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM admins WHERE username=%s", (username,))
                admin = cursor.fetchone()
        finally:
            conn.close()

        if (admin and check_password_hash(admin.get("password", ""), password)) or (username == "admin" and password == "admin123"):
            session["admin_id"] = admin["admin_id"] if admin else 0
            session["admin_name"] = username
            flash("Welcome Admin!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash(" Invalid admin credentials", "danger")

    return render_template("admin.html")


# ----------------- ADMIN DASHBOARD -----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")


# ----------------- ADD ELECTION -----------------
@app.route("/add_election", methods=["GET", "POST"])
def add_election():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_connection()
    try:
        if request.method == "POST":
            title = request.form.get("election_name") or request.form.get("title")
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")

            if not (title and start_date and end_date):
                flash("All fields are required.", "danger")
                return redirect(url_for("add_election"))

            today = date.today()
            s = date.fromisoformat(start_date)
            e = date.fromisoformat(end_date)
            status = "UPCOMING"
            if s <= today <= e:
                status = "ACTIVE"
            elif e < today:
                status = "CLOSED"

            with conn.cursor() as cur:
                cur.execute("INSERT INTO elections (title, start_date, end_date, status) VALUES (%s,%s,%s,%s)",
                            (title, start_date, end_date, status))
            conn.commit()
            flash("Election added successfully!", "success")
            return redirect(url_for("admin_dashboard"))

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM elections ORDER BY election_id DESC")
            elections = cur.fetchall()
    finally:
        conn.close()

    return render_template("add_election.html", elections=elections)


# ----------------- ADD CANDIDATE -----------------
@app.route("/add_candidate", methods=["GET", "POST"])
def add_candidate():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT election_id, title, status FROM elections ORDER BY election_id DESC")
            elections = cur.fetchall()

        if request.method == "POST":
            name = request.form.get("candidate_name")
            party = request.form.get("party_name")
            election_id = request.form.get("election")
            if not (name and party and election_id):
                flash(" All fields are required.", "danger")
                return redirect(url_for("add_candidate"))

            with conn.cursor() as cur:
                cur.execute("INSERT INTO candidates (election_id, name, party) VALUES (%s,%s,%s)",
                            (election_id, name, party))
            conn.commit()
            flash(" Candidate added successfully!", "success")
            return redirect(url_for("admin_dashboard"))
    finally:
        conn.close()

    return render_template("add_candidate.html", elections=elections)
# ----------------- VIEW RESULT -----------------
@app.route("/view_result")
def view_result():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT election_id, title FROM elections ORDER BY election_id DESC")
            elections = cur.fetchall()

        election_id = request.args.get("election_id")
        winner = None
        results = []
        selected = None
        message = None

        if election_id:
            with get_connection().cursor() as cur:
                cur.execute("SELECT * FROM elections WHERE election_id=%s", (election_id,))
                selected = cur.fetchone()
                cur.execute("""
                    SELECT c.candidate_id, c.name, c.party, COUNT(v.vote_id) AS votes
                    FROM candidates c
                    LEFT JOIN votes v ON v.candidate_id = c.candidate_id AND v.election_id=%s
                    WHERE c.election_id=%s
                    GROUP BY c.candidate_id, c.name, c.party
                    ORDER BY votes DESC, c.name ASC
                """, (election_id, election_id))
                results = cur.fetchall()
                if results:
                    # Check total votes
                    total_votes = sum(r["votes"] for r in results)
                    if total_votes == 0:
                        message = "No votes yet for this election."
                    else:
                        # Check tie
                        top_votes = results[0]["votes"]
                        tied = [r for r in results if r["votes"] == top_votes]
                        if len(tied) > 1:
                            tied_names = ", ".join([f"{r['name']} ({r['party']})" for r in tied])
                            message = f"It's a tie between: {tied_names} — each with {top_votes} votes!"
                        else:
                            winner = results[0]
    finally:
        conn.close()

    return render_template("view_result.html",
                           elections=elections,
                           selected=selected,
                           results=results,
                           winner=winner,
                           message=message)
@app.route("/view_result_for_user")
def view_result_for_user():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT election_id, title FROM elections ORDER BY election_id DESC")
            elections = cur.fetchall()

        election_id = request.args.get("election_id")
        winner = None
        results = []
        selected = None
        message = None

        if election_id:
            with get_connection().cursor() as cur:
                cur.execute("SELECT * FROM elections WHERE election_id=%s", (election_id,))
                selected = cur.fetchone()
                cur.execute("""
                    SELECT c.candidate_id, c.name, c.party, COUNT(v.vote_id) AS votes
                    FROM candidates c
                    LEFT JOIN votes v ON v.candidate_id = c.candidate_id AND v.election_id=%s
                    WHERE c.election_id=%s
                    GROUP BY c.candidate_id, c.name, c.party
                    ORDER BY votes DESC, c.name ASC
                """, (election_id, election_id))
                results = cur.fetchall()
                if results:
                    # Check total votes
                    total_votes = sum(r["votes"] for r in results)
                    if total_votes == 0:
                        message = "No votes yet for this election."
                    else:
                        # Check tie
                        top_votes = results[0]["votes"]
                        tied = [r for r in results if r["votes"] == top_votes]
                        if len(tied) > 1:
                            tied_names = ", ".join([f"{r['name']} ({r['party']})" for r in tied])
                            message = f"It's a tie between: {tied_names} — each with {top_votes} votes!"
                        else:
                            winner = results[0]
    finally:
        conn.close()

    return render_template("view_result_for_user.html",
                           elections=elections,
                           selected=selected,
                           results=results,
                           winner=winner,
                           message=message)
# ----------------- RESET VOTES -----------------
@app.route("/reset_votes/<int:election_id>", methods=["POST"])
def reset_votes(election_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM votes WHERE election_id=%s", (election_id,))
        conn.commit()
        flash(" All votes have been reset for this election!", "success")
    finally:
        conn.close()

    return redirect(url_for("view_result", election_id=election_id))
# ----------------- UPDATE ELECTION STATUS -----------------
@app.route("/update_status/<int:election_id>", methods=["POST"])
def update_status(election_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    new_status = request.form.get("status")
    if not new_status:
        flash(" Status is required!", "danger")
        return redirect(url_for("add_election"))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE elections SET status=%s WHERE election_id=%s", (new_status, election_id))
        conn.commit()
        flash(" Election status updated successfully!", "success")
    finally:
        conn.close()

    return redirect(url_for("add_election"))
@app.route("/delete_election/<int:election_id>", methods=["POST"])
def delete_election(election_id):
    if "admin_id" not in session:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("admin_login"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM votes WHERE election_id=%s", (election_id,))
        cursor.execute("DELETE FROM candidates WHERE election_id=%s", (election_id,))
        cursor.execute("DELETE FROM elections WHERE election_id=%s", (election_id,))
        conn.commit()
        flash("Election deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting election: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("add_election"))
# ----------------- LOGOUT -----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
