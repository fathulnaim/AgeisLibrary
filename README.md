# 🛡️ AegisLibrary: Secure Library Management System

AegisLibrary is a high-security, web-based inventory and identity management system. Built with a **Security-by-Design** philosophy, it provides a robust platform for managing library assets while protecting against common web vulnerabilities such as SQL Injection, Buffer Overflows, and Broken Authentication.

---

## 🌟 Key Features
- **Public Catalog:** Dynamic browsing of library assets with real-time availability statistics.
- **Advanced Search:** Case-insensitive keyword discovery for titles and unique identifiers.
- **Identity & Access Management (IAM):** Secure registration and role-based access control (RBAC) for Members and Administrators.
- **Transaction Logic:** Integrated workflow for borrowing and returning items with automated inventory updates.
- **Self-Service Recovery:** Secure "Forgot Password" workflow utilizing out-of-band OTP verification.
- **Administrative Suite:** Privileged tools for inventory management and system oversight.

---

## 🔒 Security Architecture
AegisLibrary implements multiple defensive layers to ensure the "Confidentiality, Integrity, and Availability" (CIA) of data:

| Feature | Description | Security Mitigation |
| :--- | :--- | :--- |
| **MFA (OTP)** | 2-Step Verification via 6-digit randomized tokens. | Mitigates **Broken Authentication** and Credential Stuffing. |
| **SQLi Protection** | 100% implementation of Parameterized Queries. | Prevents **SQL Injection** at the database layer. |
| **Input Validation** | Combined Syntactic (Regex) and Semantic (Length) checks. | Mitigates **XSS** and **Buffer Overflow** exploits. |
| **Secure Hashing** | PBKDF2-SHA256 salting and hashing of credentials. | Protects **Data at Rest** against disclosure. |
| **Audit Logging** | Centralized, timestamped recording of all system events. | Ensures **Accountability** and forensic readiness. |
| **PII Masking** | Obfuscation of sensitive user contact details. | Prevents **Information Disclosure** and protects privacy. |

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **Pip** (Python Package Manager)

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AegisLibrary.git
   cd AegisLibrary
