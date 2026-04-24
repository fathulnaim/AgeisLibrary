from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
import random
import time
import os

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
        if not is_valid_input(email, 50, r"^[a-zA-Z0-9.@_-]*$"):
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
        # Verify if email exists in our system
        user = db.execute("SELECT username FROM users WHERE email = ?", (email,)).fetchone()
        
        if user:
            # Generate Reset OTP
            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_email'] = email
            session['reset_time'] = time.time()
            
            print("\n" + "?"*40)
            print(f"PASSWORD RESET OTP FOR {email}: {otp}")
            print("?"*40 + "\n")
            
            return redirect('/verify_reset_otp')
        else:
            flash("Error: That email is not registered in our library.")
    return render_template('forgot_password.html')

# OTP/MFA for forget password
@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if 'reset_otp' not in session: return redirect('/forgot_password')
    
    # Check for expiration (60 seconds)
    if time.time() - session.get('reset_time', 0) > 60:
        session.pop('reset_otp', None)
        flash("Reset code expired. Please request a new one.")
        return redirect('/forgot_password')

    # Check if the code correct or not
    if request.method == 'POST':
        user_code = request.form.get('code')
        if user_code == session.get('reset_otp'):
            session['reset_authorized'] = True
            return redirect('/reset_password_final')
        else:
            flash("Invalid Reset Code!")
            
    return render_template('verify_reset_otp.html', email=session.get('reset_email'))

# Reset password here
@app.route('/reset_password_final', methods=['GET', 'POST'])
def reset_password_final():
    # SECURITY: Prevent direct access to this page
    if not session.get('reset_authorized'): return redirect('/')

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm = request.form.get('confirm')

        if len(new_password) < 8:
            flash("Password must be at least 8 characters!")
            return render_template('reset_final.html')
            
        if new_password != confirm:
            flash("Passwords do not match!")
            return render_template('reset_final.html')

        # Update Database
        db = get_db()
        hashed_pw = generate_password_hash(new_password)
        db.execute("UPDATE users SET password_hash = ? WHERE email = ?", 
                   (hashed_pw, session.get('reset_email')))
        db.commit()

        # Clean up session
        session.clear()
        flash("Success! Password updated. Please login.", "success")
        return redirect('/login_page')

    return render_template('reset_final.html')

# MFA
@app.route('/send_mfa')
def send_mfa():
    if 'temp_user' not in session: return redirect('/')
    
    # Generate new code and store the time it was created
    mfa_code = str(random.randint(100000, 999999))
    session['mfa_code'] = mfa_code
    session['mfa_time'] = time.time()
    
    print("\n" + "!"*40)
    print(f"NEW OTP FOR {session['temp_user']}: {mfa_code}")
    print(f"EXPIRES IN: 60 SECONDS")
    print("!"*40 + "\n")
    
    return redirect('/mfa')

@app.route('/mfa', methods=['GET', 'POST'])
def mfa():
    if 'mfa_code' not in session: return redirect('/')
    
    # Check the time
    current_time = time.time()
    created_time = session.get('mfa_time', 0)
    
    if current_time - created_time > 60:
        session.pop('mfa_code', None)
        flash("OTP Expired! A new code has been generated and sent.")
        return redirect('/send_mfa') # Auto-generate new code

    if request.method == 'POST':
        user_code = request.form.get('code')
        if user_code == session.get('mfa_code'):
            session['user'] = session['temp_user']
            session['role'] = session['temp_role']
            session.pop('mfa_code', None)
            return redirect('/dashboard')
        else:
            flash("Invalid Code!")
            
    email_hint = mask_email(session.get('temp_email', 'user@mail.com'))
    return render_template('mfa.html', email_hint=email_hint)

# Search route

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('book_id')
    current_user = session.get('user', 'Guest')
    add_log(current_user, "Book Search", f"Keyword used: {query}")

    # Help to prevent buffer overflow
    if len(query) > 50:
        flash("SECURITY ALERT: Search buffer exceeded! (Max 50 characters)")
        return redirect(url_for('home'))

    if not is_valid_input(query, 50, r"^[a-zA-Z0-9 ]*$"):
        flash("Input Validation Error: Invalid characters detected.", "danger")
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
    
    return render_template('dashboard.html', results=results, query=query, stats=stats, all_books=all_books, user=session.get('user'))


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
    if session.get('role') != 'admin': return redirect('/')
    
    bid = request.form.get('book_id', '')
    title = request.form.get('title', '')
    cat = request.form.get('category', '')

    db = get_db()

    # Buffer overflow prevention
    if len(bid) > 8:
        flash("CRITICAL: Buffer Overflow! Book ID is too long (Max 8).")
        
        # Fetch list of books
        all_books = db.execute("SELECT * FROM books").fetchall()
        
        # Now we send EVERYTHING: stats (if needed), books list, and sticky data
        return render_template('admin.html', 
                               books=all_books, 
                               bid=bid, 
                               title=title, 
                               cat=cat)

        # Validate search input
    if is_valid_input(bid, 8) and is_valid_input(title, 50):
        try:
            db.execute("INSERT INTO books VALUES (?, ?, ?, 'Available', NULL)", (bid, title, cat))
            db.commit()
            add_log(session['user'], "ADMIN Action: Add Book", f"Added Book ID: {bid}")
            flash("Success: Book added.")
            return redirect('/admin') # Use redirect on success to clear the form
        except Exception as e:
            flash("Error: Database Collision (ID already exists).")
            all_books = db.execute("SELECT * FROM books").fetchall()
            return render_template('admin.html', books=all_books, sticky_bid=bid, sticky_title=title)
    else:
        flash("Validation Error: Invalid characters detected.")
        all_books = db.execute("SELECT * FROM books").fetchall()
        return render_template('admin.html', books=all_books, sticky_bid=bid, sticky_title=title)

# Borrow for admin
@app.route('/admin/borrow', methods=['POST'])
def borrow():
    if session.get('role') != 'admin': return redirect('/')
    bid = request.form.get('book_id')
    db = get_db()
    db.execute("UPDATE books SET status = 'Borrowed' WHERE book_id = ?", (bid,))
    db.commit()
    # Inside admin routes:
    add_log(session['user'], "ADMIN Action: Borrow Book", f"Borrowed Book ID: {bid}")
    flash("Action Completed Successfully!", "success")
    return redirect('/admin')

# Return for admin
@app.route('/admin/return', methods=['POST'])
def return_b():
    if session.get('role') != 'admin': return redirect('/')
    
    bid = request.form.get('book_id')
    db = get_db()
    
    # Parameterized query here
    db.execute("UPDATE books SET status = 'Available', borrowed_by = NULL WHERE book_id = ?", (bid,))
    db.commit()
    
    add_log(session['user'], "ADMIN Action: Return Book", f"Returned Book ID: {bid}")
    flash(f"Management Alert: Book {bid} has been forcibly returned by Admin.")
    return redirect('/admin')

# Delete book record
@app.route('/admin/delete', methods=['POST'])
def delete_book():
    if session.get('role') != 'admin': return redirect('/')
    bid = request.form.get('book_id')
    db = get_db()
    db.execute("DELETE FROM books WHERE book_id = ?", (bid,))
    db.commit()
    add_log(session['user'], "ADMIN Action: Delete Book", f"Added Book ID: {bid}")
    flash("Book deleted!")
    return redirect('/admin')

# Student borrow features

@app.route('/borrow/<book_id>', methods=['POST'])
def student_borrow(book_id):
    if 'user' not in session: return redirect('/')
    
    db = get_db()
    # Check if book is already borrowed (Semantic Validation)
    book = db.execute("SELECT status FROM books WHERE book_id = ?", (book_id,)).fetchone()
    
    if book and book['status'] == 'Available':
        # Update status and record who borrowed it
        db.execute("UPDATE books SET status = 'Borrowed', borrowed_by = ? WHERE book_id = ?", 
               (session['user'], book_id))
        db.commit()
        add_log(session['user'], "Borrow Book", f"Book ID: {book_id}")
        flash(f"Success! You have borrowed {book_id}", "success")
    else:
        flash("This book is already borrowed by someone else!")
        
    return redirect('/dashboard')

# Student return book
@app.route('/return/<book_id>', methods=['POST'])
def student_return(book_id):
    if 'user' not in session: return redirect('/')
    
    db = get_db()
    db.execute("UPDATE books SET status = 'Available', borrowed_by = NULL WHERE book_id = ?", (book_id,))
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