document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    lucide.createIcons();

    // State Variables
    let isBalanceVisible = true;
    let actualBalance = 0;
    let selectedWallet = 'GoPay';
    let recipientDebounceTimer = null;

    // View Containers
    const authView = document.getElementById('auth-view');
    const dashboardView = document.getElementById('dashboard-view');

    // Forms
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const formDeposit = document.getElementById('form-deposit');
    const formWithdraw = document.getElementById('form-withdraw');
    const formTransfer = document.getElementById('form-transfer');
    const formTopup = document.getElementById('form-topup');

    // Modals & Backdrop
    const modalBackdrop = document.getElementById('modal-backdrop');
    const modals = document.querySelectorAll('.modal');
    const closeButtons = document.querySelectorAll('.btn-close-modal');

    // Interactive Buttons
    const btnToggleBalance = document.getElementById('btn-toggle-balance');
    const balanceEyeIcon = document.getElementById('balance-eye-icon');
    const balanceAmount = document.getElementById('balance-amount');
    const btnLogout = document.getElementById('btn-logout');

    // Switch Auth Links
    const switchToRegisterLink = document.getElementById('switch-to-register');
    const switchToLoginLink = document.getElementById('switch-to-login');

    // Transfer Recipient Preview Elements
    const transferAccountInput = document.getElementById('transfer-account');
    const recipientPreview = document.getElementById('recipient-preview');
    const recipientSpinner = document.getElementById('recipient-spinner');
    const recipientNameText = document.getElementById('recipient-name-text');

    // Toast Container
    const toastContainer = document.getElementById('toast-container');

    // ==========================================
    // TOAST NOTIFICATIONS FUNCTION
    // ==========================================
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle';
        if (type === 'error') iconName = 'alert-triangle';
        
        toast.innerHTML = `
            <i data-lucide="${iconName}" class="toast-icon"></i>
            <span class="toast-message">${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        lucide.createIcons(); // Render the new icon
        
        // Triggers the animation transition
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Remove toast after 4 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 350); // Match CSS transition duration
        }, 4000);
    }

    // ==========================================
    // AUTHENTICATION SWITCHING
    // ==========================================
    switchToRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.classList.remove('active');
        setTimeout(() => {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            setTimeout(() => {
                registerForm.classList.add('active');
            }, 10);
        }, 200);
        document.getElementById('auth-subtitle').textContent = 'Mulai langkah finansial barumu sekarang.';
    });

    switchToLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.classList.remove('active');
        setTimeout(() => {
            registerForm.style.display = 'none';
            loginForm.style.display = 'block';
            setTimeout(() => {
                loginForm.classList.add('active');
            }, 10);
        }, 200);
        document.getElementById('auth-subtitle').textContent = 'Masa depan perbankan digital di tanganmu.';
    });

    // ==========================================
    // API CALLS (REGISTER, LOGIN, LOGOUT, LOAD DATA)
    // ==========================================
    
    // Register Request
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('reg-name').value;
        const username = document.getElementById('reg-username').value;
        const password = document.getElementById('reg-password').value;
        const pin = document.getElementById('reg-pin').value;

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, username, password, pin })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                registerForm.reset();
                switchToLoginLink.click();
            } else {
                showToast(data.message || 'Pendaftaran gagal.', 'error');
            }
        } catch (error) {
            showToast('Terjadi kesalahan koneksi internet.', 'error');
        }
    });

    // Login Request
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                loginForm.reset();
                
                // Switch view to dashboard
                authView.classList.add('hidden');
                dashboardView.classList.remove('hidden');
                
                // Load user data
                loadDashboardData();
            } else {
                showToast(data.message || 'Login gagal.', 'error');
            }
        } catch (error) {
            showToast('Terjadi kesalahan koneksi internet.', 'error');
        }
    });

    // Logout Request
    btnLogout.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/logout', { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                showToast(data.message, 'success');
                // Switch view back to Login
                dashboardView.classList.add('hidden');
                authView.classList.remove('hidden');
            }
        } catch (error) {
            showToast('Gagal melakukan logout.', 'error');
        }
    });

    // Load User and Account Data
    async function loadDashboardData() {
        try {
            const response = await fetch('/api/user-info');
            const data = await response.json();

            if (data.success) {
                const user = data.user;
                
                // Update text elements
                document.getElementById('user-display-name').textContent = user.name;
                document.getElementById('user-avatar-initial').textContent = user.name.charAt(0).toUpperCase();
                document.getElementById('welcome-name').textContent = user.name.split(' ')[0];
                document.getElementById('card-user-name').textContent = user.name.toUpperCase();
                
                // Formatted Account Number: e.g. 8809 1234 5678
                const rawAcc = user.account_number;
                const formattedAcc = rawAcc.replace(/(\d{4})(\d{4})(\d{2})/, '$1 $2 $3');
                document.getElementById('card-account-number').textContent = formattedAcc;

                // Update Balance
                actualBalance = user.balance;
                renderBalance();

                // Update Transactions List
                renderTransactions(user.transactions);
            } else {
                showToast('Sesi Anda berakhir. Silakan login kembali.', 'error');
                dashboardView.classList.add('hidden');
                authView.classList.remove('hidden');
            }
        } catch (error) {
            showToast('Gagal memuat data dari server.', 'error');
        }
    }

    // Format money helper: 100000 -> 100.000
    function formatCurrency(amount) {
        return new Intl.NumberFormat('id-ID').format(amount);
    }

    // Render balance with show/hide eye logic
    function renderBalance() {
        if (isBalanceVisible) {
            balanceAmount.textContent = formatCurrency(actualBalance);
            balanceEyeIcon.setAttribute('data-lucide', 'eye');
        } else {
            balanceAmount.textContent = '••••••';
            balanceEyeIcon.setAttribute('data-lucide', 'eye-off');
        }
        lucide.createIcons();
    }

    btnToggleBalance.addEventListener('click', () => {
        isBalanceVisible = !isBalanceVisible;
        renderBalance();
    });

    // Render Transaction List
    function renderTransactions(transactions) {
        const listContainer = document.getElementById('transactions-list');
        const countBadge = document.getElementById('transaction-count');
        
        countBadge.textContent = `${transactions.length} Transaksi`;

        if (transactions.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <i data-lucide="receipt" class="empty-icon"></i>
                    <p>Belum ada aktivitas transaksi.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        let html = '';
        transactions.forEach(tx => {
            let title = '';
            let amountSign = '';
            let amountClass = '';
            let iconName = 'arrow-down-left';
            let refLabel = tx.reference;

            switch (tx.type) {
                case 'setor':
                    title = 'Setor Tunai';
                    amountSign = '+';
                    amountClass = 'positive';
                    iconName = 'arrow-down-left';
                    break;
                case 'tarik':
                    title = 'Tarik Tunai';
                    amountSign = '-';
                    amountClass = 'negative';
                    iconName = 'arrow-up-right';
                    break;
                case 'transfer_masuk':
                    title = 'Transfer Masuk';
                    amountSign = '+';
                    amountClass = 'positive';
                    iconName = 'arrow-down-left';
                    break;
                case 'transfer_keluar':
                    title = 'Transfer Uang';
                    amountSign = '-';
                    amountClass = 'negative';
                    iconName = 'arrow-up-right';
                    break;
                case 'topup':
                    title = 'Top Up E-Wallet';
                    amountSign = '-';
                    amountClass = 'negative';
                    iconName = 'smartphone';
                    break;
            }

            html += `
                <div class="tx-item">
                    <div class="tx-left">
                        <div class="tx-icon-badge ${tx.type}">
                            <i data-lucide="${iconName}" class="tx-icon"></i>
                        </div>
                        <div class="tx-details">
                            <span class="tx-title">${title}</span>
                            <span class="tx-reference">${refLabel}</span>
                            <span class="tx-time">${tx.timestamp}</span>
                        </div>
                    </div>
                    <div class="tx-right">
                        <span class="tx-amount ${amountClass}">${amountSign} Rp ${formatCurrency(tx.amount)}</span>
                    </div>
                </div>
            `;
        });

        listContainer.innerHTML = html;
        lucide.createIcons();
    }

    // Check if session already exists on load
    (async function checkSession() {
        try {
            const response = await fetch('/api/user-info');
            const data = await response.json();
            if (data.success) {
                authView.classList.add('hidden');
                dashboardView.classList.remove('hidden');
                loadDashboardData();
            }
        } catch (error) {
            // Silently fail if no session
        }
    })();

    // ==========================================
    // MODALS CONTROLLER & BACKDROP
    // ==========================================
    
    // Open Modals
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('click', () => {
            const modalId = card.getAttribute('data-modal');
            const modal = document.getElementById(modalId);
            
            // Show backdrop and active modal
            modalBackdrop.classList.remove('hidden');
            modal.classList.remove('hidden');
            setTimeout(() => {
                modalBackdrop.style.opacity = '1';
                modal.classList.add('active');
            }, 10);
        });
    });

    // Close Modal helper
    function closeModal() {
        const activeModal = document.querySelector('.modal.active');
        if (!activeModal) return;

        activeModal.classList.remove('active');
        modalBackdrop.style.opacity = '0';
        
        setTimeout(() => {
            activeModal.classList.add('hidden');
            modalBackdrop.classList.add('hidden');
            
            // Reset modal forms and previews on close
            formDeposit.reset();
            formWithdraw.reset();
            formTransfer.reset();
            formTopup.reset();
            
            recipientPreview.className = 'recipient-preview hidden';
            recipientNameText.textContent = '';
        }, 300);
    }

    closeButtons.forEach(btn => btn.addEventListener('click', closeModal));
    modalBackdrop.addEventListener('click', closeModal);

    // Amount Preset Button Handlers
    const presetButtons = document.querySelectorAll('.preset-btn');
    presetButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const amount = btn.getAttribute('data-amount');
            const parentForm = btn.closest('form');
            const inputField = parentForm.querySelector('input[type="number"]');
            if (inputField) {
                inputField.value = amount;
            }
        });
    });

    // ==========================================
    // TRANSACTION FORMS SUBMISSION
    // ==========================================

    // 1. Setor Tunai Submission
    formDeposit.addEventListener('submit', async (e) => {
        e.preventDefault();
        const amount = document.getElementById('deposit-amount').value;

        try {
            const response = await fetch('/api/deposit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                closeModal();
                loadDashboardData();
            } else {
                showToast(data.message || 'Setor tunai gagal.', 'error');
            }
        } catch (error) {
            showToast('Kesalahan koneksi internet.', 'error');
        }
    });

    // 2. Tarik Tunai Submission
    formWithdraw.addEventListener('submit', async (e) => {
        e.preventDefault();
        const amount = document.getElementById('withdraw-amount').value;
        const pin = document.getElementById('withdraw-pin').value;

        try {
            const response = await fetch('/api/withdraw', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount, pin })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                closeModal();
                loadDashboardData();
            } else {
                showToast(data.message || 'Tarik tunai gagal.', 'error');
            }
        } catch (error) {
            showToast('Kesalahan koneksi internet.', 'error');
        }
    });

    // 3. Debounced Recipient Verification for Transfer
    transferAccountInput.addEventListener('input', () => {
        const accountNum = transferAccountInput.value.trim();
        
        clearTimeout(recipientDebounceTimer);
        recipientPreview.className = 'recipient-preview hidden';
        recipientNameText.textContent = '';

        if (accountNum.length < 10) return;

        // Show spinner
        recipientPreview.className = 'recipient-preview';
        recipientSpinner.classList.remove('hidden');

        recipientDebounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/recipient-info?account_number=${accountNum}`);
                const data = await response.json();

                recipientSpinner.classList.add('hidden');
                if (data.success) {
                    recipientPreview.classList.add('success');
                    recipientNameText.textContent = `Penerima: ${data.recipient_name}`;
                } else {
                    recipientPreview.classList.add('error');
                    recipientNameText.textContent = data.message || 'Nomor rekening tidak valid.';
                }
            } catch (error) {
                recipientSpinner.classList.add('hidden');
                recipientPreview.classList.add('error');
                recipientNameText.textContent = 'Koneksi gagal memverifikasi rekening.';
            }
        }, 600); // 600ms debounce delay
    });

    // Transfer Submission
    formTransfer.addEventListener('submit', async (e) => {
        e.preventDefault();
        const recipient_account = transferAccountInput.value.trim();
        const amount = document.getElementById('transfer-amount').value;
        const pin = document.getElementById('transfer-pin').value;

        try {
            const response = await fetch('/api/transfer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ recipient_account, amount, pin })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                closeModal();
                loadDashboardData();
            } else {
                showToast(data.message || 'Transfer gagal.', 'error');
            }
        } catch (error) {
            showToast('Kesalahan koneksi internet.', 'error');
        }
    });

    // 4. Wallet Selector Grid
    const walletOptions = document.querySelectorAll('.wallet-option');
    walletOptions.forEach(opt => {
        opt.addEventListener('click', () => {
            walletOptions.forEach(o => o.classList.remove('active'));
            opt.classList.add('active');
            selectedWallet = opt.getAttribute('data-wallet');
        });
    });

    // Top Up Submission
    formTopup.addEventListener('submit', async (e) => {
        e.preventDefault();
        const phone_number = document.getElementById('topup-phone').value.trim();
        const amount = document.getElementById('topup-amount').value;
        const pin = document.getElementById('topup-pin').value;

        try {
            const response = await fetch('/api/topup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    wallet_name: selectedWallet, 
                    phone_number, 
                    amount, 
                    pin 
                })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                closeModal();
                loadDashboardData();
            } else {
                showToast(data.message || 'Top up gagal.', 'error');
            }
        } catch (error) {
            showToast('Kesalahan koneksi internet.', 'error');
        }
    });
});
