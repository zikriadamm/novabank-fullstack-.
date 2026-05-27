import os
import sqlite3
from bank_system import BankSystem

def run_tests():
    print("=== Memulai Pengujian Backend NovaBank ===")
    
    # 1. Bersihkan database lama untuk testing jika ada
    db_path = 'novabank.db'
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Database lama dibersihkan.")
        except PermissionError:
            print("Database sedang digunakan, melanjutkan dengan database saat ini.")

    # 2. Inisialisasi Bank System
    bank = BankSystem(db_path)
    print("BankSystem berhasil diinisialisasi dan tabel database dibuat.")

    # 3. Uji Registrasi Pengguna Baru
    print("\n--- Menguji Registrasi ---")
    try:
        # User 1: Alice
        success1, acc_alice = bank.register_user("Alice Margatroid", "alice", "alice123", "123456")
        print(f"Alice terdaftar. Rekening: {acc_alice} (Diberi saldo bonus awal)")
        
        # User 2: Bob
        success2, acc_bob = bank.register_user("Bob Ross", "bobross", "bob12345", "654321")
        print(f"Bob terdaftar. Rekening: {acc_bob} (Diberi saldo bonus awal)")
        
    except Exception as e:
        print(f"FAILED: Registrasi gagal. Error: {e}")
        return

    # 4. Uji Autentikasi Kredensial
    print("\n--- Menguji Autentikasi ---")
    try:
        user_alice = bank.authenticate_user("alice", "alice123")
        print(f"Autentikasi Alice berhasil. Pemilik Rekening: {user_alice.name}")
        
        # Uji password salah
        try:
            bank.authenticate_user("alice", "password_salah")
            print("FAILED: Harusnya gagal karena password salah, tapi malah sukses.")
        except ValueError as e:
            print(f"SUCCESS: Deteksi password salah berhasil: {e}")
            
    except Exception as e:
        print(f"FAILED: Autentikasi bermasalah. Error: {e}")
        return

    # 5. Uji Setor Tunai (Deposit)
    print("\n--- Menguji Setor Tunai ---")
    conn = bank._get_connection()
    try:
        acc = bank.get_account(conn, user_alice.account.account_number)
        print(f"Saldo awal Alice: Rp {acc.balance:,.2f}")
        
        # Setor Rp 50.000
        acc.deposit(conn, 50000.0)
        print(f"Setor tunai Rp 50,000. Saldo sekarang: Rp {acc.balance:,.2f}")
        
        if acc.balance != 150000.0:
            print(f"FAILED: Saldo Alice harusnya Rp 150,000.00 tapi bernilai Rp {acc.balance:,.2f}")
            
    except Exception as e:
        print(f"FAILED: Setor tunai bermasalah. Error: {e}")
    finally:
        conn.close()

    # 6. Uji Tarik Tunai (Withdraw)
    print("\n--- Menguji Tarik Tunai ---")
    conn = bank._get_connection()
    try:
        acc = bank.get_account(conn, user_alice.account.account_number)
        
        # Tarik dengan PIN salah
        try:
            acc.withdraw(conn, 20000.0, "111111", user_alice.pin)
            print("FAILED: Penarikan dengan PIN salah harusnya gagal, tapi malah sukses.")
        except ValueError as e:
            print(f"SUCCESS: Deteksi PIN penarikan salah berhasil: {e}")

        # Tarik melebihi saldo
        try:
            acc.withdraw(conn, 9999999.0, "123456", user_alice.pin)
            print("FAILED: Penarikan melebihi saldo harusnya gagal, tapi malah sukses.")
        except ValueError as e:
            print(f"SUCCESS: Deteksi saldo tidak cukup berhasil: {e}")

        # Tarik sukses Rp 30.000
        acc.withdraw(conn, 30000.0, "123456", user_alice.pin)
        print(f"Tarik tunai Rp 30,000 berhasil. Saldo sekarang: Rp {acc.balance:,.2f}")
        
        if acc.balance != 120000.0:
            print(f"FAILED: Saldo Alice harusnya Rp 120,000.00 tapi bernilai Rp {acc.balance:,.2f}")

    except Exception as e:
        print(f"FAILED: Tarik tunai bermasalah. Error: {e}")
    finally:
        conn.close()

    # 7. Uji Transfer ke Rekening Lain
    print("\n--- Menguji Transfer ---")
    conn = bank._get_connection()
    try:
        sender_acc = bank.get_account(conn, user_alice.account.account_number)
        recipient_acc = bank.get_account(conn, acc_bob)
        
        print(f"Saldo awal Bob: Rp {recipient_acc.balance:,.2f}")
        
        # Transfer Rp 40.000 ke Bob
        sender_acc.transfer(conn, recipient_acc, 40000.0, "123456", user_alice.pin)
        print(f"Transfer Rp 40,000 dari Alice ke Bob berhasil.")
        
        # Ambil kembali data saldo terbaru dari DB
        alice_new = bank.get_account(conn, user_alice.account.account_number)
        bob_new = bank.get_account(conn, acc_bob)
        
        print(f"Saldo Alice setelah transfer: Rp {alice_new.balance:,.2f}")
        print(f"Saldo Bob setelah menerima transfer: Rp {bob_new.balance:,.2f}")
        
        if alice_new.balance != 80000.0 or bob_new.balance != 140000.0:
            print("FAILED: Perhitungan saldo transfer tidak sesuai.")
            
    except Exception as e:
        print(f"FAILED: Proses transfer bermasalah. Error: {e}")
    finally:
        conn.close()

    # 8. Uji Top Up E-Wallet
    print("\n--- Menguji Top Up E-Wallet ---")
    conn = bank._get_connection()
    try:
        acc = bank.get_account(conn, user_alice.account.account_number)
        
        # Top Up OVO Rp 25.000
        acc.topup_ewallet(conn, "OVO", "081234567890", 25000.0, "123456", user_alice.pin)
        
        # Ambil data saldo terbaru
        acc_updated = bank.get_account(conn, user_alice.account.account_number)
        print(f"Top Up OVO Rp 25,000 berhasil. Saldo Alice sekarang: Rp {acc_updated.balance:,.2f}")
        
        if acc_updated.balance != 55000.0:
            print(f"FAILED: Saldo Alice harusnya Rp 55,000.00 tapi bernilai Rp {acc_updated.balance:,.2f}")
            
    except Exception as e:
        print(f"FAILED: Top up bermasalah. Error: {e}")
    finally:
        conn.close()

    # 9. Memeriksa Riwayat Transaksi
    print("\n--- Memeriksa Riwayat Transaksi ---")
    conn = bank._get_connection()
    try:
        acc = bank.get_account(conn, user_alice.account.account_number)
        acc.load_transactions(conn)
        print(f"Jumlah transaksi Alice: {len(acc.transactions)}")
        print("Detail Transaksi Alice (Terbaru -> Terlama):")
        for tx in acc.transactions:
            print(f"  - [{tx.timestamp}] {tx.type.upper()}: Rp {tx.amount:,.2f} | Ref/Ket: {tx.reference}")
            
    except Exception as e:
        print(f"FAILED: Memuat transaksi bermasalah. Error: {e}")
    finally:
        conn.close()

    print("\n=== Pengujian Backend NovaBank Selesai ===")

if __name__ == '__main__':
    run_tests()
