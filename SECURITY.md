---

## 1. Authentication & Session Management
AegisLibrary utilizes a state-based authentication workflow to prevent session hijacking:
*   **Step 1:** Primary credentials are verified against stored hashes.
*   **Step 2:** A temporary, restricted session is created (`temp_user`).
*   **Step 3:** The user is redirected to the MFA portal. Access to the Dashboard or Admin routes is blocked until the `mfa_code` is validated.
*   **Expiration:** MFA tokens expire automatically after 60 seconds to prevent replay attacks.

## 2. Mitigation of Injection Attacks
To mitigate **SQL Injection (SQLi)**, the system strictly avoids string concatenation in database queries. 
*   **Implementation:** All database calls utilize `sqlite3` parameterization. 
*   **Example:** `db.execute("SELECT * FROM books WHERE book_id = ?", (book_id,))`

## 3. Application-Level Buffer Safety
While the underlying Python environment is memory-safe, we prevent resource exhaustion and logic bypasses via:
*   **UI Constraints:** `maxlength` attributes on all `<input>` fields.
*   **Backend Guards:** Centralized validation logic that rejects any input exceeding pre-defined buffers (e.g., 8 characters for Book IDs, 30 for Usernames).

## 4. Security Auditing & Monitoring
The system maintains a non-repudiable audit log in the `logs` table. Every significant interaction is recorded:
*   **Events Logged:** Successful/Failed logins, password changes, book searches, and administrative inventory changes.
*   **Data Points:** Timestamp, User ID, Activity Category, and specific action details.

## 5. Privacy & Data Protection
*   **Password Hashing:** Utilizing `werkzeug.security` with `PBKDF2-SHA256`.
*   **Masking:** Personally Identifiable Information (PII) like email addresses are partially masked on the UI during the MFA process to mitigate information disclosure risks.
