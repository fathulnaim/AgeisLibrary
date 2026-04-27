import sqlite3
from werkzeug.security import generate_password_hash

def initialize():
    connection = sqlite3.connect('library.db')
    with open('schema.sql') as f:
        connection.executescript(f.read())
    cursor = connection.cursor()

    # 1. Initialize user and admin
    cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                   ("admin", "admin@library.com", generate_password_hash("admin123"), "admin"))

    # 2. List of books (Tambah 'None' di hujung setiap baris untuk due_date)
    sample_books = [
        ('SCI00001', 'Quantum Mechanics', 'Science', 'Available', None, None),
        ('SCI00002', 'Microbiology Basics', 'Science', 'Available', None, None),
        ('SCI00003', 'Astrophysics for All', 'Science', 'Available', None, None),
        ('MTH00001', 'Linear Algebra', 'Math', 'Available', None, None),
        ('MTH00002', 'Discrete Mathematics', 'Math', 'Available', None, None),
        ('MTH00003', 'Statistical Analysis', 'Math', 'Available', None, None),
        ('FIC00001', '1984 by George Orwell', 'Fiction', 'Available', None, None),
        ('FIC00002', 'The Great Gatsby', 'Fiction', 'Available', None, None),
        ('FIC00003', 'Brave New World', 'Fiction', 'Available', None, None),
        ('HIS00001', 'The Roman Empire', 'History', 'Available', None, None),
        ('HIS00002', 'Malaysian History', 'History', 'Available', None, None),
        ('HIS00003', 'Industrial Revolution', 'History', 'Available', None, None),
        ('TEC00001', 'Ethical Hacking 101', 'Technology', 'Available', None, None),
        ('TEC00002', 'Blockchain Revolution', 'Technology', 'Available', None, None),
        ('TEC00003', 'Artificial Intelligence', 'Technology', 'Available', None, None),
        ('ART00001', 'Leonardo da Vinci Life', 'Art', 'Available', None, None),
        ('ART00002', 'Digital Illustration', 'Art', 'Available', None, None),
        ('ART00003', 'History of Photography', 'Art', 'Available', None, None),
        ('LIT00001', 'Shakespeare Sonnets', 'Literature', 'Available', None, None),
        ('LIT00002', 'The Odyssey', 'Literature', 'Available', None, None),
        ('LIT00003', 'Poetry of the World', 'Literature', 'Available', None, None),
        ('PHL00001', 'Beyond Good and Evil', 'Philosophy', 'Available', None, None),
        ('PHL00002', 'Meditations - Aurelius', 'Philosophy', 'Available', None, None),
        ('PHL00003', 'The Republic - Plato', 'Philosophy', 'Available', None, None)
    ]
    
    # Guna 6 tanda soal (?) kerana sekarang ada 6 kolum
    cursor.executemany("INSERT INTO books VALUES (?, ?, ?, ?, ?, ?)", sample_books)

    connection.commit()
    connection.close()
    print("--------------------------------------------------")
    print("SUCCESS: library.db created with 6-column schema!")
    print("--------------------------------------------------")

if __name__ == '__main__':
    initialize()