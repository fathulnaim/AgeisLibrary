import sqlite3
from werkzeug.security import generate_password_hash

def initialize():
    connection = sqlite3.connect('library.db')
    with open('schema.sql') as f:
        connection.executescript(f.read())
    cursor = connection.cursor()

    # 1. To initialize user and admin
    cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                   ("admin", "admin@library.com", generate_password_hash("admin1234"), "admin"))
    cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                   ("naim", "naim@gmail.com", generate_password_hash("naim1234"), "user"))

    # 2. List of books
    sample_books = [
        ('SCI00001', 'Quantum Mechanics', 'Science', 'Available', None),
        ('SCI00002', 'Microbiology Basics', 'Science', 'Available', None),
        ('SCI00003', 'Astrophysics for All', 'Science', 'Available', None),
        ('MTH00001', 'Linear Algebra', 'Math', 'Available', None),
        ('MTH00002', 'Discrete Mathematics', 'Math', 'Available', None),
        ('MTH00003', 'Statistical Analysis', 'Math', 'Available', None),
        ('FIC00001', '1984 by George Orwell', 'Fiction', 'Available', None),
        ('FIC00002', 'The Great Gatsby', 'Fiction', 'Available', None),
        ('FIC00003', 'Brave New World', 'Fiction', 'Available', None),
        ('HIS00001', 'The Roman Empire', 'History', 'Available', None),
        ('HIS00002', 'Malaysian History', 'History', 'Available', None),
        ('HIS00003', 'Industrial Revolution', 'History', 'Available', None),
        ('TEC00001', 'Ethical Hacking 101', 'Technology', 'Available', None),
        ('TEC00002', 'Blockchain Revolution', 'Technology', 'Available', None),
        ('TEC00003', 'Artificial Intelligence', 'Technology', 'Available', None),
        ('ART00001', 'Leonardo da Vinci Life', 'Art', 'Available', None),
        ('ART00002', 'Digital Illustration', 'Art', 'Available', None),
        ('ART00003', 'History of Photography', 'Art', 'Available', None),
        ('LIT00001', 'Shakespeare Sonnets', 'Literature', 'Available', None),
        ('LIT00002', 'The Odyssey', 'Literature', 'Available', None),
        ('LIT00003', 'Poetry of the World', 'Literature', 'Available', None),
        ('PHL00001', 'Beyond Good and Evil', 'Philosophy', 'Available', None),
        ('PHL00002', 'Meditations - Aurelius', 'Philosophy', 'Available', None),
        ('PHL00003', 'The Republic - Plato', 'Philosophy', 'Available', None)
    ]
    
    # We use 5 question marks because there are now 5 columns
    cursor.executemany("INSERT INTO books VALUES (?, ?, ?, ?, ?)", sample_books)

    connection.commit()
    connection.close()
    print("--------------------------------------------------")
    print("SUCCESS: library.db created with 24 sample books!")
    print("--------------------------------------------------")

if __name__ == '__main__':
    initialize()