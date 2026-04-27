from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
import random
import time
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# Validation
def is_valid_input(data, max_len, pattern=r"^[a-zA-Z0-9.@_-]*$"):
    if not data or len(str(data)) > max_len:
        return False
    return bool(re.match(pattern, str(data)))

# DB connection
def get_db():
    conn = sqlite3.connect('library.db', timeout=20) 
    conn.row_factory = sqlite3.Row
    return conn

def add_log(username, activity, details=""):
    try:
        db = get_db()
        db.execute("INSERT INTO logs (username, activity, details) VALUES (?, ?, ?)", 
                   (username, activity, details))
        db.commit()
    except Exception as e:
        print(f"Logging Error: {e}")
    finally:
        db.close()
#Hint for OTP/MFA
def mask_email(email):
    try:
        # Splits 'fathul@email.com' into 'fathul' and 'email.com'
        user, domain = email.split('@')
        # Returns 'f' + '***' + '@email.com' -> f***@email.com
        return user[0] + user[1] + "***" + "@" + domain
    except:
        return "****@mail.com"

#Home Route
@app.route('/')
def home():
    db = get_db()
    
    #1. Fetch book status
    total_books = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available_books = db.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'").fetchone()[0]
    borrowed_books = db.execute("SELECT COUNT(*) FROM books WHERE status = 'Borrowed'").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    
    # 2. Fetch  borrowed book
    my_books_count = 0
    if session.get('user'):
        my_books_count = db.execute("SELECT COUNT(*) FROM books WHERE borrowed_by = ?", 
                                     (session['user'],)).fetchone()[0]

    # 3. Fetch all books
    all_books = db.execute("SELECT * FROM books").fetchall()
    
    stats = {
        'total': total_books,
        'available': available_books,
        'rented': borrowed_books,
        'my_books': my_books_count, # This is the "My Borrowed" stat
        'users': total_users
    }
    current_user = session.get('user')
    
    return render_template('dashboard.html', 
                           user=current_user,
                           role=session.get('role'), 
                           stats=stats, 
                           all_books=all_books)

# Redirect to dashboard
@app.route('/dashboard')
def dashboard():
    return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # 1. INITIALIZE variables here so they exist
    username = None
    email = None

    if request.method == 'POST':
        # Get data from form
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check 1: Username format
        if not is_valid_input(username, 30, r"^[a-zA-Z0-9._-]*$"):
            flash("Invalid characters in username!", "danger")
            return render_template('signup.html', username=username, email=email)

        # Check 2: Email format
        if not is_valid_input(email, 50, r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.com$"):
            flash("Invalid email format!", "danger")
            return render_template('signup.html', username=username, email=email)
        
        # Check 3: Password Length
        if len(password) < 8:
            flash("Security Alert: Password is too short! Must be at least 8 characters.", "danger")
            return render_template('signup.html', username=username, email=email)

        try:
            db = get_db()
            db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                       (username, email, generate_password_hash(password), 'user'))
            db.commit()
            
            session['temp_user'] = username
            session['temp_email'] = email
            session['temp_role'] = 'user'
            return redirect('/send_mfa')
        except Exception as e:
            flash("Username or Email already exists!", "danger")
            return render_template('signup.html', username=username, email=email)

    # 3. This line now works for the first visit because variables are None
    return render_template('signup.html', username=username, email=email)

# Login page route
@app.route('/login_page')
def login_page():
    return render_template('login.html')

# MFA
@app.route('/send_mfa')
def send_mfa():
    if 'temp_user' not in session: return redirect('/')
    
    # Generate new code and store the time it was created
    mfa_code = str(random.randint(100000, 999999))
    session['mfa_attempts'] = 3
    session['mfa_code'] = mfa_code
    session['mfa_time'] = time.time()
    
    print("\n" + "!"*40)
    print(f"NEW OTP FOR {session['temp_email']}: {mfa_code}")
    print(f"EXPIRES IN: 60 SECONDS")
    print("!"*40 + "\n")
    
    return redirect('/mfa')

@app.route('/mfa', methods=['GET', 'POST'])
def mfa():
    # Security: If no MFA process is active, kick to login
    if 'mfa_code' not in session: return redirect('/login_page')
    username = session.get('temp_user')
    # --- TIME CALCULATION ---
    now = time.time()
    remaining = int(60 - (now - session.get('mfa_time', now)))

    if request.method == 'POST':
        # --- SCENARIO 1: EXPIRED OTP ---
        if remaining <= 0:
            add_log(username, "MFA Verification Failed", "Failed - Code Expired")
            flash("OTP Expired! Please click the 'Resend' button.", "danger")
            return render_template('mfa.html', remaining_time=0, 
                                   attempts=session.get('mfa_attempts'),
                                   email_hint=mask_email(session.get('temp_email')))

        user_code = request.form.get('code')

        # --- VALIDATION LOGIC ---
        if user_code == session.get('mfa_code'):
            # SUCCESS: Move user to session
            add_log(username, "MFA Verification", "Success - Fully Logged In")
            session['user'] = session['temp_user']
            session['role'] = session['temp_role']
            # Clean up all MFA keys
            for key in ['mfa_code', 'mfa_time', 'mfa_attempts', 'mfa_resends', 'temp_user', 'temp_role']:
                session.pop(key, None)
            return redirect('/dashboard')

        else:
            # --- SCENARIO 2: INPUT ATTEMPTS EXCEEDED ---
            session['mfa_attempts'] = session.get('mfa_attempts', 3) - 1
            
            if session['mfa_attempts'] <= 0:
                add_log(username, "MFA Verification Blocked", "Blocked - Too many wrong codes")
                session.clear() # Kill everything for security
                flash("Too many failed attempts. Identity could not be verified. Please log in again.", "danger")
                return redirect('/login_page')
            add_log(username, "MFA Verification Failed", f"Failed - Wrong code. {session['mfa_attempts']} tries left")
            flash(f"Invalid Code! {session['mfa_attempts']} tries remaining.", "danger")
            
    return render_template('mfa.html', 
                           email_hint=mask_email(session.get('temp_email')), 
                           remaining_time=max(0, remaining),
                           attempts=session.get('mfa_attempts'))

@app.route('/resend_mfa')
def resend_mfa():
    if 'temp_email' not in session: return redirect('/login_page')
    username = session.get('temp_user')
    resends = session.get('mfa_resends', 0)
    if resends >= 3:
        add_log(username, "MFA Resend Blocked", "Blocked - Max resends reached")
        session.clear()
        flash("Resend limit reached. For security, please wait and log in again later.", "danger")
        return redirect('/login_page')

    # Reset MFA state for the new code
    new_mfa = str(random.randint(100000, 999999))
    session['mfa_code'] = new_mfa
    session['mfa_time'] = time.time()
    session['mfa_attempts'] = 3
    session['mfa_resends'] = resends + 1

    # 4. Send the Email (Use your existing email function here)
    print("\n" + "!"*40)
    print(f"NEW OTP FOR {session['temp_email']}: {new_mfa}")
    print(f"EXPIRES IN: 60 SECONDS")
    print("!"*40 + "\n")

    add_log(username, "MFA Resend", f"Success - Resend #{session['mfa_resends']}")
    flash(f"A new code has been sent! (Resend {session['mfa_resends']}/3)", "success")
    return redirect('/mfa')

# Submission handler for login
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    
    if user and check_password_hash(user['password_hash'], password):
        session['temp_user'] = username
        session['temp_email'] = user['email'] # Store email for MFA display
        session['temp_role'] = user['role']
        session['resend_count'] = 0
        add_log(username, "Login Attempt", "Successful password entry, moving to MFA")
        return redirect('/send_mfa')
    
    add_log(username if username else "Unknown", "Login Failed", "Invalid credentials entered")
    flash("Invalid credentials!", "danger")
    return render_template('login.html', username=username)

# Reset password handler by asking email
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        db = get_db()
        user = db.execute("SELECT username FROM users WHERE email = ?", (email,)).fetchone()
        
        if user:
            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_email'] = email
            session['reset_time'] = time.time()
            session['reset_attempts'] = 3
            session['reset_resend_count'] = 0
            
            # LOG: Reset started
            add_log(email, "Reset Requested", "Generated first OTP")
            print("\n" + "!"*40)
            print(f"NEW OTP FOR {email}: {otp}")
            print(f"EXPIRES IN: 60 SECONDS")
            print("!"*40 + "\n")
            
            return redirect('/verify_reset_otp')
        else:
            # LOG: Failed attempt to find email
            add_log(email, "Reset Request Failed", "Failed - Email not found in DB")
            flash("Error: That email is not registered.", "danger")
            
    return render_template('forgot_password.html')

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if 'reset_otp' not in session: return redirect('/forgot_password')
    
    email = session.get('reset_email')
    remaining = int(60 - (time.time() - session.get('reset_time', time.time())))
    
    if request.method == 'POST':
        # 1. Check if expired
        if remaining <= 0:
            add_log(email, "OTP Verification Failed", "Failed - Code Expired")
            flash("Code expired! Please resend.", "danger")
            return render_template('verify_reset_otp.html', remaining_time=0, attempts=session.get('reset_attempts'))

        user_code = request.form.get('code')
        
        # 2. Check if correct
        if user_code == session.get('reset_otp'):
            add_log(email, "OTP Verification", "Success")
            session['reset_authorized'] = True
            session.pop('reset_otp', None)
            return redirect('/reset_password_final')
        
        # 3. Handle wrong code
        else:
            session['reset_attempts'] = session.get('reset_attempts', 3) - 1
            
            if session['reset_attempts'] <= 0:
                add_log(email, "OTP Verification Blocked", "Account Locked - Max Attempts reached")
                session.clear()
                flash("Too many failed attempts. Start over.", "danger")
                return redirect('/forgot_password')
            
            add_log(email, "OTP Verification Failed", f"Failed - Wrong code. {session['reset_attempts']} tries left")
            flash(f"Invalid code! {session['reset_attempts']} tries left.", "danger")

    return render_template('verify_reset_otp.html', 
                           remaining_time=max(0, remaining), 
                           attempts=session.get('reset_attempts', 3))

@app.route('/resend_reset_otp')
def resend_reset_otp():
    if 'reset_email' not in session: return redirect('/forgot_password')
    email = session.get('reset_email')

    # Check resend limit
    resend_count = session.get('reset_resend_count', 0)
    if resend_count >= 3:
        add_log(email, "OTP Resend Blocked", "Blocked - Max resends reached")
        flash("Too many resends. Please try again later.", "danger")
        return redirect('/forgot_password')

    # Reset for new OTP
    otp = str(random.randint(100000, 999999))
    session['reset_otp'] = otp
    session['reset_time'] = time.time()
    session['reset_attempts'] = 3
    session['reset_resend_count'] = resend_count + 1

    print("\n" + "!"*40)
    print(f"NEW OTP FOR {email}: {otp}")
    print(f"EXPIRES IN: 60 SECONDS")
    print("!"*40 + "\n")
            
    add_log(email, "OTP Resend", f"Success - Resend #{session['reset_resend_count']}")
    flash(f"New reset code sent! (Resend {session['reset_resend_count']}/3)", "success")
    return redirect('/verify_reset_otp')

@app.route('/reset_password_final', methods=['GET', 'POST'])
def reset_password_final():
    if not session.get('reset_authorized'): return redirect('/')
    email = session.get('reset_email')

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm = request.form.get('confirm')

        # Simple check (you should add your regex password check here too)
        if len(new_password) < 8 or new_password != confirm:
            flash("Invalid password or mismatch!", "danger")
            return render_template('reset_final.html')

        # Update DB
        db = get_db()
        hashed_pw = generate_password_hash(new_password)
        db.execute("UPDATE users SET password_hash = ? WHERE email = ?", (hashed_pw, email))
        db.commit()

        # LOG: FINAL SUCCESS
        add_log(email, "Password Change", "Success - User updated password")

        session.clear()
        flash("Success! Password updated. Please login.", "success")
        return redirect('/login_page')

    return render_template('reset_final.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('book_id')
    current_user = session.get('user', 'Guest')
    current_role = session.get('role')
    add_log(current_user, "Book Search", f"Keyword used: {query}")

    # Help to prevent buffer overflow
    if len(query) > 50:
        flash("SECURITY ALERT: Search buffer exceeded! (Max 50 characters)")
        add_log(session['user'],"Input Validation Failed",f"Keyword rejected: {query} | Reason: Input length exceeded")
        return redirect(url_for('home'))

    if not is_valid_input(query, 50, r"^[a-zA-Z0-9 ]*$"):
        flash("Input Validation Error: Invalid characters detected.", "danger")
        add_log(current_user,"Input Validation Failed",f"Keyword rejected: {query} | Reason: Invalid characters / Harmful pattern detected")
        return redirect(url_for('home'))

    db = get_db()
    # Parameterized Search to prevent injection
    sql = "SELECT * FROM books WHERE book_id LIKE ? OR title LIKE ?"
    results = db.execute(sql, (f'%{query}%', f'%{query}%')).fetchall()
    
    # Re-fetch stats for dashboard
    total_books = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    available_books = db.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'").fetchone()[0]
    borrowed_books = db.execute("SELECT COUNT(*) FROM books WHERE status = 'Borrowed'").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    all_books = db.execute("SELECT * FROM books").fetchall()
    stats = {'total': total_books, 'available': available_books, 'rented': borrowed_books, 'my_books': 0, 'users': total_users}
    
    return render_template('dashboard.html', results=results, query=query, stats=stats, all_books=all_books, user=session.get('user'), role=current_role)


# Admin features

@app.route('/admin')
def admin():
    if session.get('role') != 'admin': return redirect('/')
    db = get_db()
    books = db.execute("SELECT * FROM books").fetchall()
    return render_template('admin.html', books=books)

# Admin add new book
@app.route('/admin/add', methods=['POST'])
def add_book():
    if session.get('role') != 'admin':
        return redirect('/')

    bid = request.form.get('book_id', '')
    title = request.form.get('title', '')
    cat = request.form.get('category', '')

    db = get_db()

    try:
        if len(bid) > 8:
            flash("CRITICAL: Book ID too long (Max 8).", "danger")
            db.close()
            add_log(session.get('user', 'Unknown'),
                    "Buffer Overflow Attempt Blocked",
                    f"Book ID: {bid}")
            return redirect('/admin')

        if not is_valid_input(bid, 8) or not is_valid_input(title, 50, r"^[a-zA-Z0-9\s.,-/]*$"):
            flash("Validation Error: Invalid characters detected.", "danger")
            db.close()
            return redirect('/admin')

        db.execute(
            "INSERT INTO books VALUES (?, ?, ?, 'Available', NULL, NULL)",
            (bid, title, cat)
        )
        db.commit()
        db.close()

        add_log(session.get('user', 'Unknown'),
                "ADMIN Action: Add Book",
                f"Added Book ID: {bid}")

        flash("Success: Book added.", "success")
        return redirect('/admin')

    except Exception:
        db.close()

        add_log(session.get('user', 'Unknown'),
                "Book Add Failed",
                f"Book ID: {bid}")

        flash("Error: Book ID already exists or DB error.", "danger")
        return redirect('/admin')

# Borrow for admin
@app.route('/admin/borrow', methods=['POST'])
def borrow():
    if session.get('role') != 'admin': return redirect('/')
    
    bid = request.form.get('book_id')
    duration = int(request.form.get('duration', 7)) 
    
    db = get_db()
    due_date = (datetime.now() + timedelta(days=duration)).strftime('%Y-%m-%d')
    
    db.execute("UPDATE books SET status = 'Borrowed', borrowed_by = ?, due_date = ? WHERE book_id = ?", 
               (session['user'], due_date, bid))
    db.commit()
    
    add_log(session['user'], "ADMIN Action: Borrow Book", f"Book ID: {bid} (Due: {due_date})")
    flash(f"Book borrowed for {duration} days. Due: {due_date}", "success")
    return redirect('/admin')
# Return for admin
@app.route('/admin/return', methods=['POST'])
def return_b():
    if session.get('role') != 'admin': return redirect('/')
    
    bid = request.form.get('book_id')
    db = get_db()
    
    db.execute("UPDATE books SET status = 'Available', borrowed_by = NULL, due_date = NULL WHERE book_id = ?", (bid,))
    db.commit()
    
    add_log(session['user'], "ADMIN Action: Return Book", f"Returned Book ID: {bid}")
    flash(f"Management Alert: Book {bid} has been forcibly returned by Admin.", "warning")
    return redirect('/admin')

# Delete book record
@app.route('/admin/delete', methods=['POST'])
def delete_book():
    if session.get('role') != 'admin':
        return redirect('/')

    bid = request.form.get('book_id')
    db = get_db()

    # Check from books table
    book = db.execute(
        "SELECT status FROM books WHERE book_id = ?",
        (bid,)
    ).fetchone()

    if not book:
        flash("Book not found.", "danger")
        return redirect('/admin')

    if book['status'] == 'Borrowed':
        flash("Cannot delete: Book is currently borrowed.", "danger")

        add_log(
            session['user'],
            "Delete Book Blocked",
            f"Delete rejected | Book ID: {bid} | Reason: Book is currently borrowed"
        )

        return redirect('/admin')

    # Safe to delete
    db.execute("DELETE FROM books WHERE book_id = ?", (bid,))
    db.commit()

    add_log(
        session['user'],
        "ADMIN Action: Delete Book",
        f"Deleted Book ID: {bid}"
    )

    flash("Book deleted!", "success")
    return redirect('/admin')

# Student borrow features

@app.route('/borrow/<book_id>', methods=['POST'])
def student_borrow(book_id):
    if 'user' not in session: return redirect('/')
    
    # 1. Ambil durasi dari pilihan student (3, 7, 14, 21)
    duration_days = int(request.form.get('duration', 7)) 
    
    # 2. Kira tarikh pulangkan (Hari ini + X hari)
    due_date = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d')
    
    db = get_db()
    book = db.execute("SELECT status FROM books WHERE book_id = ?", (book_id,)).fetchone()
    
    if book and book['status'] == 'Available':

        db.execute("UPDATE books SET status = 'Borrowed', borrowed_by = ?, due_date = ? WHERE book_id = ?", 
               (session['user'], due_date, book_id))
        db.commit()
        
        add_log(session['user'], "Borrow Book", f"ID: {book_id}, Due: {due_date} ({duration_days} days)")
        flash(f"Borrowed! Please return by {due_date}", "success")
    else:
        flash("Book is not available.", "danger")
        
    return redirect('/dashboard')

# Student return book
@app.route('/return/<book_id>', methods=['POST'])
def student_return(book_id):
    if 'user' not in session: return redirect('/')
    
    db = get_db()
    db.execute("UPDATE books SET status = 'Available', borrowed_by = NULL, due_date = NULL WHERE book_id = ?", (book_id,))
    db.commit()
    
    add_log(session['user'], "Return Book", f"Book ID: {book_id}")
    flash(f"Book {book_id} has been returned. Thank you!", "success")
    return redirect('/dashboard')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session: return redirect('/')
    
    db = get_db()
    # 1. Get User Info
    user_info = db.execute("SELECT * FROM users WHERE username = ?", (session['user'],)).fetchone()
    
    # 2. Get ONLY books borrowed by this user
    my_books = db.execute("SELECT * FROM books WHERE borrowed_by = ?", (session['user'],)).fetchall()

    if request.method == 'POST':
        # Change Password Logic
        old_pass = request.form.get('old_password')
        new_pass = request.form.get('new_password')
        
        if check_password_hash(user_info['password_hash'], old_pass):
            if len(new_pass) >= 8:
                hashed = generate_password_hash(new_pass)
                db.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed, session['user']))
                db.commit()
                add_log(session['user'], "Security Action: Password Changed", "User successfully updated their password.")
                flash("Password updated successfully!", "success")
            else:
                add_log(session['user'], "Security Alert: Password Change Failed", "Attempted to use a password shorter than 8 characters.")
                flash("New password too short!", "warning")
        else:
            add_log(session['user'], "Security Alert: Password Change Failed", "Incorrect current password entered.")
            flash("Current password incorrect!", "danger")
        return redirect('/profile')

    return render_template('profile.html', user=user_info, books=my_books)

@app.route('/admin/logs')
def admin_logs():
    if session.get('role') != 'admin': return redirect('/')
    db = get_db()
    # Fetch logs, latest first
    all_logs = db.execute("SELECT * FROM logs ORDER BY timestamp DESC").fetchall()
    return render_template('admin_logs.html', logs=all_logs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)