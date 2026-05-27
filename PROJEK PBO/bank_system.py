import sqlite3
import random
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'novabank.db')

class Transaction:
    def __init__(self, transaction_id, account_number, trans_type, amount, reference, timestamp=None):
        self.transaction_id = transaction_id
        self.account_number = account_number
        self.type = trans_type  # 'setor', 'tarik', 'transfer_masuk', 'transfer_keluar', 'topup'
        self.amount = float(amount)
        self.reference = reference  # E-wallet name, recipient account number, or notes
        self.timestamp = timestamp or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self):
        return {
            'id': self.transaction_id,
            'account_number': self.account_number,
            'type': self.type,
            'amount': self.amount,
            'reference': self.reference,
            'timestamp': self.timestamp
        }


from abc import ABC, abstractmethod

# 1. ABSTRAKSI (Abstraction)
# Menggunakan Abstract Base Class (ABC) untuk mendefinisikan kontrak akun bank umum
class BankAccount(ABC):
    def __init__(self, account_number, balance=0.0):
        # 2. ENKAPSULASI (Encapsulation)
        # Data disembunyikan menggunakan variabel internal (_account_number, _balance)
        # dan hanya diekspos secara terkontrol menggunakan decorator @property (getter/setter)
        self._account_number = account_number
        self._balance = float(balance)
        self.transactions = []

    @property
    def account_number(self):
        return self._account_number

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        # Enkapsulasi memungkinkan kita memvalidasi data sebelum memperbarui state objek
        if value < 0:
            raise ValueError("Saldo tidak boleh negatif.")
        self._balance = float(value)

    # Metode abstrak yang harus diimplementasikan oleh kelas turunan
    @abstractmethod
    def get_account_type(self):
        pass


# 3. PEWARISAN (Inheritance)
# Kelas Account mewarisi properti dan metode dari kelas abstrak BankAccount
class Account(BankAccount):
    def __init__(self, account_number, balance=0.0):
        super().__init__(account_number, balance)

    # 4. POLIMORFISME (Polymorphism)
    # Meng-override (menimpa) metode get_account_type untuk memberikan identitas spesifik
    def get_account_type(self):
        return "Tabungan Digital NovaBank"


    def load_transactions(self, conn):
        self.transactions = []
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, type, amount, reference, timestamp FROM transactions WHERE account_number = ? ORDER BY timestamp DESC",
            (self.account_number,)
        )
        for row in cursor.fetchall():
            self.transactions.append(Transaction(row[0], self.account_number, row[1], row[2], row[3], row[4]))

    def deposit(self, conn, amount):
        if amount <= 0:
            raise ValueError("Jumlah setoran harus lebih besar dari nol.")
        
        self.balance += amount
        cursor = conn.cursor()
        
        # Update balance in DB
        cursor.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (self.balance, self.account_number))
        
        # Log transaction
        cursor.execute(
            "INSERT INTO transactions (account_number, type, amount, reference, timestamp) VALUES (?, ?, ?, ?, ?)",
            (self.account_number, 'setor', amount, 'Setor Tunai Mandiri', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        
        conn.commit()
        self.load_transactions(conn)
        return True

    def withdraw(self, conn, amount, pin, user_pin):
        if amount <= 0:
            raise ValueError("Jumlah penarikan harus lebih besar dari nol.")
        if amount > self.balance:
            raise ValueError("Saldo tidak mencukupi untuk melakukan penarikan.")
        if pin != user_pin:
            raise ValueError("PIN yang Anda masukkan salah.")
            
        self.balance -= amount
        cursor = conn.cursor()
        
        # Update balance in DB
        cursor.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (self.balance, self.account_number))
        
        # Log transaction
        cursor.execute(
            "INSERT INTO transactions (account_number, type, amount, reference, timestamp) VALUES (?, ?, ?, ?, ?)",
            (self.account_number, 'tarik', amount, 'Tarik Tunai Mandiri', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        
        conn.commit()
        self.load_transactions(conn)
        return True

    def transfer(self, conn, recipient_account, amount, pin, user_pin):
        if amount <= 0:
            raise ValueError("Jumlah transfer harus lebih besar dari nol.")
        if amount > self.balance:
            raise ValueError("Saldo tidak mencukupi untuk melakukan transfer.")
        if pin != user_pin:
            raise ValueError("PIN yang Anda masukkan salah.")
        if recipient_account.account_number == self.account_number:
            raise ValueError("Tidak dapat mentransfer ke rekening sendiri.")
            
        # Deduct sender
        self.balance -= amount
        # Add recipient
        recipient_account.balance += amount
        
        cursor = conn.cursor()
        
        # Update balances
        cursor.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (self.balance, self.account_number))
        cursor.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (recipient_account.balance, recipient_account.account_number))
        
        # Log sender transaction
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO transactions (account_number, type, amount, reference, timestamp) VALUES (?, ?, ?, ?, ?)",
            (self.account_number, 'transfer_keluar', amount, f"Ke Rek. {recipient_account.account_number}", now)
        )
        # Log recipient transaction
        cursor.execute(
            "INSERT INTO transactions (account_number, type, amount, reference, timestamp) VALUES (?, ?, ?, ?, ?)",
            (recipient_account.account_number, 'transfer_masuk', amount, f"Dari Rek. {self.account_number}", now)
        )
        
        conn.commit()
        self.load_transactions(conn)
        return True

    def topup_ewallet(self, conn, wallet_name, phone_number, amount, pin, user_pin):
        if amount <= 0:
            raise ValueError("Jumlah top up harus lebih besar dari nol.")
        if amount > self.balance:
            raise ValueError("Saldo tidak mencukupi untuk melakukan top up.")
        if pin != user_pin:
            raise ValueError("PIN yang Anda masukkan salah.")
        if not phone_number.isdigit() or len(phone_number) < 10 or len(phone_number) > 13:
            raise ValueError("Nomor handphone tidak valid. Harus berupa angka 10-13 digit.")
            
        self.balance -= amount
        cursor = conn.cursor()
        
        # Update balance
        cursor.execute("UPDATE accounts SET balance = ? WHERE account_number = ?", (self.balance, self.account_number))
        
        # Log transaction
        cursor.execute(
            "INSERT INTO transactions (account_number, type, amount, reference, timestamp) VALUES (?, ?, ?, ?, ?)",
            (self.account_number, 'topup', amount, f"{wallet_name} ({phone_number})", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        
        conn.commit()
        self.load_transactions(conn)
        return True


class User:
    def __init__(self, user_id, name, username, password_hash, pin, account=None):
        self.user_id = user_id
        self.name = name
        self.username = username
        self.password_hash = password_hash
        self.pin = pin
        self.account = account

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'username': self.username,
            'account': {
                'account_number': self.account.account_number,
                'balance': self.account.balance
            } if self.account else None
        }


class BankSystem:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Enable Foreign Keys
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Users Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                pin TEXT NOT NULL
            );
            """)
            
            # Accounts Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_number TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                balance REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)
            
            # Transactions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                reference TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (account_number) REFERENCES accounts(account_number) ON DELETE CASCADE
            );
            """)
            conn.commit()

    def generate_unique_account_number(self, conn):
        while True:
            # Generate a 10 digit number starting with 88 (e.g. 88xxxxxxxx)
            acc_num = "88" + "".join([str(random.randint(0, 9)) for _ in range(8)])
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM accounts WHERE account_number = ?", (acc_num,))
            if cursor.fetchone() is None:
                return acc_num

    def register_user(self, name, username, password, pin):
        # Validations
        if not name or not username or not password or not pin:
            raise ValueError("Semua data input harus diisi.")
        if len(pin) != 6 or not pin.isdigit():
            raise ValueError("PIN harus terdiri dari 6 digit angka.")
        if len(username) < 4:
            raise ValueError("Username minimal harus 4 karakter.")
        if len(password) < 6:
            raise ValueError("Password minimal harus 6 karakter.")

        hashed_password = generate_password_hash(password)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Insert User
            cursor.execute(
                "INSERT INTO users (name, username, password_hash, pin) VALUES (?, ?, ?, ?)",
                (name, username, hashed_password, pin)
            )
            user_id = cursor.lastrowid
            
            # Generate Account
            account_number = self.generate_unique_account_number(conn)
            cursor.execute(
                "INSERT INTO accounts (account_number, user_id, balance) VALUES (?, ?, ?)",
                (account_number, user_id, 0.0)
            )
            
            # Give a welcome bonus of Rp 100,000 for attractive starting balance!
            cursor.execute(
                "UPDATE accounts SET balance = 100000.0 WHERE account_number = ?",
                (account_number,)
            )
            cursor.execute(
                "INSERT INTO transactions (account_number, type, amount, reference, timestamp) VALUES (?, ?, ?, ?, ?)",
                (account_number, 'setor', 100000.0, 'Welcome Reward NovaBank', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            
            conn.commit()
            return True, account_number
        except sqlite3.IntegrityError:
            conn.rollback()
            raise ValueError("Username sudah digunakan. Silakan pilih username lain.")
        finally:
            conn.close()

    def authenticate_user(self, username, password):
        if not username or not password:
            raise ValueError("Username dan password harus diisi.")
            
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT u.id, u.name, u.username, u.password_hash, u.pin, a.account_number, a.balance "
                "FROM users u JOIN accounts a ON u.id = a.user_id "
                "WHERE u.username = ?",
                (username,)
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("Username tidak ditemukan.")
                
            user_id, name, db_username, password_hash, pin, account_number, balance = row
            
            if not check_password_hash(password_hash, password):
                raise ValueError("Password yang Anda masukkan salah.")
                
            # Construct OOP structure
            account = Account(account_number, balance)
            account.load_transactions(conn)
            user = User(user_id, name, db_username, password_hash, pin, account)
            return user
        finally:
            conn.close()

    def get_account(self, conn, account_number):
        cursor = conn.cursor()
        cursor.execute("SELECT account_number, balance FROM accounts WHERE account_number = ?", (account_number,))
        row = cursor.fetchone()
        if row is None:
            return None
        return Account(row[0], row[1])

    def get_user_by_account_number(self, conn, account_number):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT u.id, u.name, u.username, u.password_hash, u.pin, a.balance "
            "FROM users u JOIN accounts a ON u.id = a.user_id "
            "WHERE a.account_number = ?",
            (account_number,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        user_id, name, username, password_hash, pin, balance = row
        account = Account(account_number, balance)
        account.load_transactions(conn)
        return User(user_id, name, username, password_hash, pin, account)
