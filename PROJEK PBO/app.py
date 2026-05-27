import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from bank_system import BankSystem

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Inisialisasi BankSystem
bank = BankSystem()

def get_current_user():
    """Mengambil object User yang sedang login berdasarkan session."""
    if 'account_number' not in session:
        return None
    
    conn = bank._get_connection()
    try:
        user = bank.get_user_by_account_number(conn, session['account_number'])
        return user
    finally:
        conn.close()

@app.route('/')
def index():
    # Menampilkan antarmuka web (single page app)
    # Jika session ada, user akan diarahkan ke dashboard, jika tidak ke login/register
    return render_template('index.html')

@app.route('/api/user-info', methods=['GET'])
def user_info():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Sesi telah berakhir atau tidak valid. Silakan login kembali.'}), 401
    
    # Ambil transaksi terbaru
    transactions = [t.to_dict() for t in user.account.transactions]
    
    return jsonify({
        'success': True,
        'user': {
            'name': user.name,
            'username': user.username,
            'account_number': user.account.account_number,
            'balance': user.account.balance,
            'transactions': transactions
        }
    })

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    pin = data.get('pin', '')
    
    try:
        success, account_number = bank.register_user(name, username, password, pin)
        if success:
            return jsonify({
                'success': True, 
                'message': f'Registrasi berhasil! Selamat datang di NovaBank. Nomor Rekening Anda: {account_number}. Anda mendapatkan saldo awal bonus Rp 100.000!'
            })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': 'Terjadi kesalahan sistem. Silakan coba beberapa saat lagi.'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    try:
        user = bank.authenticate_user(username, password)
        session['user_id'] = user.user_id
        session['account_number'] = user.account.account_number
        session['name'] = user.name
        
        return jsonify({
            'success': True,
            'message': f'Selamat datang kembali, {user.name}!',
            'user': {
                'name': user.name,
                'account_number': user.account.account_number
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': 'Gagal melakukan login. Silakan periksa kredensial Anda.'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Berhasil keluar dari akun.'})

@app.route('/api/deposit', methods=['POST'])
def deposit():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Sesi tidak valid.'}), 401
        
    data = request.get_json() or {}
    try:
        amount = float(data.get('amount', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Jumlah setoran tidak valid.'}), 400
        
    conn = bank._get_connection()
    try:
        # Load user and account state fresh in connection
        account = bank.get_account(conn, user.account.account_number)
        account.deposit(conn, amount)
        return jsonify({
            'success': True,
            'message': f'Setor tunai berhasil sebesar Rp {amount:,.0f}!',
            'new_balance': account.balance
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Sesi tidak valid.'}), 401
        
    data = request.get_json() or {}
    pin = data.get('pin', '')
    try:
        amount = float(data.get('amount', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Jumlah penarikan tidak valid.'}), 400
        
    conn = bank._get_connection()
    try:
        account = bank.get_account(conn, user.account.account_number)
        account.withdraw(conn, amount, pin, user.pin)
        return jsonify({
            'success': True,
            'message': f'Tarik tunai berhasil sebesar Rp {amount:,.0f}!',
            'new_balance': account.balance
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/recipient-info', methods=['GET'])
def recipient_info():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Sesi tidak valid.'}), 401
        
    recipient_acc_num = request.args.get('account_number', '').strip()
    if recipient_acc_num == user.account.account_number:
        return jsonify({'success': False, 'message': 'Tidak dapat mentransfer ke rekening sendiri.'}), 400
        
    conn = bank._get_connection()
    try:
        recipient_user = bank.get_user_by_account_number(conn, recipient_acc_num)
        if not recipient_user:
            return jsonify({'success': False, 'message': 'Nomor rekening tidak ditemukan.'}), 404
            
        return jsonify({
            'success': True,
            'recipient_name': recipient_user.name
        })
    finally:
        conn.close()

@app.route('/api/transfer', methods=['POST'])
def transfer():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Sesi tidak valid.'}), 401
        
    data = request.get_json() or {}
    recipient_acc_num = data.get('recipient_account', '').strip()
    pin = data.get('pin', '')
    try:
        amount = float(data.get('amount', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Jumlah transfer tidak valid.'}), 400
        
    conn = bank._get_connection()
    try:
        sender_account = bank.get_account(conn, user.account.account_number)
        recipient_account = bank.get_account(conn, recipient_acc_num)
        if not recipient_account:
            return jsonify({'success': False, 'message': 'Rekening penerima tidak ditemukan.'}), 404
            
        sender_account.transfer(conn, recipient_account, amount, pin, user.pin)
        return jsonify({
            'success': True,
            'message': f'Transfer berhasil sebesar Rp {amount:,.0f} ke Rekening {recipient_acc_num}!',
            'new_balance': sender_account.balance
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/topup', methods=['POST'])
def topup():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Sesi tidak valid.'}), 401
        
    data = request.get_json() or {}
    wallet_name = data.get('wallet_name', '').strip()
    phone_number = data.get('phone_number', '').strip()
    pin = data.get('pin', '')
    try:
        amount = float(data.get('amount', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Jumlah top up tidak valid.'}), 400
        
    conn = bank._get_connection()
    try:
        account = bank.get_account(conn, user.account.account_number)
        account.topup_ewallet(conn, wallet_name, phone_number, amount, pin, user.pin)
        return jsonify({
            'success': True,
            'message': f'Top Up {wallet_name} sebesar Rp {amount:,.0f} ke {phone_number} berhasil!',
            'new_balance': account.balance
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
