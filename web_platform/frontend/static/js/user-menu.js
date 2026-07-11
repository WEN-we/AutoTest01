// 用户菜单功能模块
// 提供头像上传、修改用户名、修改密码等功能

async function getPublicKey() {
    try {
        const response = await fetch('/api/auth/public-key');
        const data = await response.json();
        if (data.code === 200) {
            return data.data.public_key;
        }
    } catch (e) {
        console.error('获取公钥失败:', e);
    }
    return null;
}

class UserMenu {
    constructor() {
        // 确定正确的 API 基础路径
        this.API_BASE = '/api';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadUserInfo();
    }

    setupEventListeners() {
        const userMenuBtn = document.querySelector('.user-menu-btn');
        const userMenuWrapper = document.querySelector('.user-menu-wrapper');

        if (userMenuBtn && userMenuWrapper) {
            userMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                userMenuWrapper.classList.toggle('open');
            });

            document.addEventListener('click', (e) => {
                if (!userMenuWrapper.contains(e.target)) {
                    userMenuWrapper.classList.remove('open');
                }
            }, { capture: true });
        }

        const editProfileBtn = document.getElementById('editProfileBtn');
        if (editProfileBtn) {
            editProfileBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.openEditProfileModal();
            });
        }

        const avatarUploadBtn = document.getElementById('uploadAvatarBtn');
        if (avatarUploadBtn) {
            avatarUploadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.openAvatarUploadModal();
            });
        }

        const changeUsernameBtn = document.getElementById('changeUsernameBtn');
        if (changeUsernameBtn) {
            changeUsernameBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.openChangeUsernameModal();
            });
        }

        const changePasswordBtn = document.getElementById('changePasswordBtn');
        if (changePasswordBtn) {
            changePasswordBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.openChangePasswordModal();
            });
        }

        const deleteAccountBtn = document.getElementById('deleteAccountBtn');
        if (deleteAccountBtn) {
            deleteAccountBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.confirmDeleteAccount();
            });
        }

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.logout();
            });
        }

        // 已移除有问题的 show.bs.modal 全局拦截器
        // 用户菜单使用自定义 createModal 方法，不依赖 Bootstrap 模态框事件
    }

    async loadUserInfo() {
        try {
            const data = await API.auth.getProfile();
            const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
            const updatedUser = { ...currentUser, ...data.data };
            localStorage.setItem('user', JSON.stringify(updatedUser));
            this.updateUserDisplay(data.data);
        } catch (error) {
            this.updateUserDisplayFromStorage();
        }
    }

    updateUserDisplayFromStorage() {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        this.updateUserDisplay({
            username: user.username || '用户',
            email: user.email || '-',
            nickname: user.nickname || '',
            avatar_url: user.avatar_url || null
        });
    }

    updateUserDisplay(user) {
        const smallAvatars = document.querySelectorAll('.user-avatar');
        const smallPlaceholders = document.querySelectorAll('.user-avatar-placeholder');
        const largeAvatars = document.querySelectorAll('.user-avatar-large');
        const largePlaceholders = document.querySelectorAll('.user-avatar-large-placeholder');
        const userName = document.querySelector('.user-name');
        const userFullname = document.querySelector('.user-fullname');
        const userEmail = document.querySelector('.user-email');

        if (user && user.avatar_url) {
            const avatarUrlWithCacheBust = user.avatar_url + '?t=' + Date.now();
            
            smallAvatars.forEach(avatar => {
                avatar.src = avatarUrlWithCacheBust;
                avatar.style.display = 'block';
            });
            
            largeAvatars.forEach(avatar => {
                avatar.src = avatarUrlWithCacheBust;
                avatar.style.display = 'block';
            });
            
            smallPlaceholders.forEach(placeholder => {
                placeholder.style.display = 'none';
            });
            largePlaceholders.forEach(placeholder => {
                placeholder.style.display = 'none';
            });
        } else {
            const username = (user && user.username) || '用户';
            const initials = username.charAt(0).toUpperCase();
            
            smallPlaceholders.forEach(placeholder => {
                placeholder.textContent = initials;
                placeholder.style.display = 'flex';
            });
            
            largePlaceholders.forEach(placeholder => {
                placeholder.textContent = initials;
                placeholder.style.display = 'flex';
            });
            
            smallAvatars.forEach(avatar => {
                avatar.style.display = 'none';
            });
            largeAvatars.forEach(avatar => {
                avatar.style.display = 'none';
            });
        }

        if (userName) userName.textContent = (user && user.nickname) || (user && user.username) || '用户';
        if (userFullname) userFullname.textContent = (user && user.nickname) || (user && user.username) || '用户';
        if (userEmail) userEmail.textContent = (user && user.email) || '-';
    }

    createModal(title, content, onConfirm) {
        this.closeAllModals();

        const modal = document.createElement('div');
        modal.className = 'user-menu-modal';
        modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1060; display: flex; align-items: center; justify-content: center; pointer-events: none;';

        modal.innerHTML = `
            <div class="modal-backdrop" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1;"></div>
            <div class="modal-dialog modal-md" style="position: relative; z-index: 2; width: 100%; max-width: 500px; margin: 0 auto; pointer-events: auto;">
                <div class="modal-content" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                    <div class="modal-header" style="padding: 16px 20px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
                        <h5 class="modal-title" style="margin: 0; color: var(--text-primary); font-size: 18px;">${title}</h5>
                        <button type="button" class="btn-close modal-close-btn" style="opacity: 0.7; background: none; border: none; font-size: 20px; cursor: pointer;">&times;</button>
                    </div>
                    <div class="modal-body" style="padding: 20px; color: var(--text-primary);">${content}</div>
                    <div class="modal-footer" style="padding: 16px 20px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; gap: 10px;">
                        <button type="button" class="btn btn-secondary modal-cancel-btn" style="padding: 8px 16px; cursor: pointer;">取消</button>
                        <button type="button" class="btn btn-primary modal-confirm-btn" style="padding: 8px 16px; cursor: pointer;">确认</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const backdrop = modal.querySelector('.modal-backdrop');
        const closeBtn = modal.querySelector('.modal-close-btn');
        const cancelBtn = modal.querySelector('.modal-cancel-btn');
        const confirmBtn = modal.querySelector('.modal-confirm-btn');

        // Stop propagation for all modal interactive elements
        modal.addEventListener('click', (e) => e.stopPropagation());
        modal.addEventListener('mousedown', (e) => e.stopPropagation());
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                modal.remove();
            }
            e.stopPropagation();
        });

        const closeModal = () => {
            modal.remove();
        };

        backdrop.addEventListener('click', (e) => { e.stopPropagation(); closeModal(); });
        if (closeBtn) closeBtn.addEventListener('click', (e) => { e.stopPropagation(); closeModal(); });
        if (cancelBtn) cancelBtn.addEventListener('click', (e) => { e.stopPropagation(); closeModal(); });

        if (onConfirm && confirmBtn) {
            confirmBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                onConfirm(modal, closeModal);
            });
        }

        return modal;
    }

    closeAllModals() {
        const modals = document.querySelectorAll('.user-menu-modal');
        modals.forEach(modal => modal.remove());
    }

    openEditProfileModal() {
        this.closeAllModals();
        const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

        this.createModal('编辑个人资料', `
            <div class="mb-3">
                <label class="form-label">昵称</label>
                <input type="text" id="profileNickname" class="form-control" 
                       placeholder="请输入昵称" value="${currentUser.nickname || ''}">
            </div>
            <div class="mb-3">
                <label class="form-label">邮箱</label>
                <input type="email" id="profileEmail" class="form-control" 
                       placeholder="请输入邮箱" value="${currentUser.email || ''}">
            </div>
        `, async (modal, closeModal) => {
            const nickname = modal.querySelector('#profileNickname').value.trim();
            const email = modal.querySelector('#profileEmail').value.trim();

            try {
                await API.auth.updateProfile(nickname, email);
                showToast('资料更新成功', 'success');
                const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
                localStorage.setItem('user', JSON.stringify({ ...currentUser, nickname, email }));
                this.loadUserInfo();
                closeModal();
            } catch (error) {
                showToast(error.message || '更新失败', 'error');
            }
        });
    }

    openAvatarUploadModal() {
        this.closeAllModals();

        const modal = this.createModal('上传头像', `
            <div class="mb-4">
                <label class="form-label">选择头像图片</label>
                <input type="file" id="avatarFile" accept="image/*" class="form-control" style="padding: 6px;">
            </div>
            <div class="mb-3 text-center">
                <img id="avatarPreview" src="" alt="预览" class="img-fluid rounded-circle" 
                     style="max-width: 120px; display: none; border: 2px solid var(--border-color);">
            </div>
        `, async (modalElement, closeModal) => {
            const fileInput = modalElement.querySelector('#avatarFile');
            if (!fileInput || !fileInput.files[0]) {
                showToast('请选择图片文件', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('avatar', fileInput.files[0]);

            try {
                const headers = {
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                };
                const res = await fetch(`${this.API_BASE}/auth/avatar`, {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });

                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.message || '上传失败');
                }

                const data = await res.json();
                showToast('头像上传成功', 'success');
                const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
                localStorage.setItem('user', JSON.stringify({ ...currentUser, avatar_url: data.data.avatar_url }));
                this.loadUserInfo();
                closeModal();
            } catch (error) {
                showToast(error.message || '上传失败', 'error');
            }
        });

        const fileInput = modal.querySelector('#avatarFile');
        const preview = modal.querySelector('#avatarPreview');

        if (fileInput && preview) {
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        preview.src = event.target.result;
                        preview.style.display = 'inline-block';
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    }

    openChangeUsernameModal() {
        this.closeAllModals();
        const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

        this.createModal('修改用户名', `
            <div class="mb-4">
                <label class="form-label">新用户名</label>
                <input type="text" id="newUsername" class="form-control" 
                       placeholder="请输入新用户名" value="${currentUser.username || ''}" required>
            </div>
        `, async (modal, closeModal) => {
            const newUsername = modal.querySelector('#newUsername').value.trim();
            if (!newUsername) {
                showToast('请输入用户名', 'error');
                return;
            }

            try {
                await API.auth.updateUsername(newUsername);
                showToast('用户名修改成功', 'success');
                const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
                localStorage.setItem('user', JSON.stringify({ ...currentUser, username: newUsername }));
                this.loadUserInfo();
                closeModal();
            } catch (error) {
                showToast(error.message || '修改失败', 'error');
            }
        });
    }

    openChangePasswordModal() {
        this.closeAllModals();

        this.createModal('修改密码', `
            <div class="mb-3">
                <label class="form-label">原密码</label>
                <input type="password" id="oldPassword" class="form-control" 
                       placeholder="请输入原密码" required>
            </div>
            <div class="mb-3">
                <label class="form-label">新密码</label>
                <input type="password" id="newPassword" class="form-control" 
                       placeholder="请输入新密码" required>
                <div class="form-text">密码长度8-32个字符，需包含字母和数字</div>
            </div>
            <div class="mb-4">
                <label class="form-label">确认新密码</label>
                <input type="password" id="confirmPassword" class="form-control" 
                       placeholder="请再次输入新密码" required>
            </div>
        `, async (modal, closeModal) => {
            const oldPasswordInput = modal.querySelector('#oldPassword');
            const newPasswordInput = modal.querySelector('#newPassword');
            const confirmPasswordInput = modal.querySelector('#confirmPassword');

            if (!oldPasswordInput || !newPasswordInput || !confirmPasswordInput) {
                showToast('内部错误', 'error');
                return;
            }

            const oldPassword = oldPasswordInput.value;
            const newPassword = newPasswordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            if (!oldPassword) {
                showToast('请输入原密码', 'error');
                return;
            }

            if (!newPassword) {
                showToast('请输入新密码', 'error');
                return;
            }

            if (!confirmPassword) {
                showToast('请确认新密码', 'error');
                return;
            }

            if (newPassword.length < 8 || newPassword.length > 32) {
                showToast('密码长度需在8-32个字符之间', 'error');
                return;
            }

            if (!/(?=.*[a-zA-Z])(?=.*[0-9])/.test(newPassword)) {
                showToast('密码需包含字母和数字', 'error');
                return;
            }

            if (newPassword !== confirmPassword) {
                showToast('两次输入的新密码不一致', 'error');
                return;
            }

            try {
                const publicKey = await getPublicKey();
                let encryptedOldPassword = oldPassword;
                let encryptedNewPassword = newPassword;
                if (publicKey) {
                    encryptedOldPassword = await PasswordCrypto.encryptPassword(oldPassword, publicKey);
                    encryptedNewPassword = await PasswordCrypto.encryptPassword(newPassword, publicKey);
                }
                await API.auth.changePassword(encryptedOldPassword, encryptedNewPassword);
                showToast('密码修改成功', 'success');
                closeModal();
            } catch (error) {
                showToast(error.message || '修改失败', 'error');
            }
        });
    }

    confirmDeleteAccount() {
        this.closeAllModals();

        this.createModal('注销账号', `
            <div class="alert alert-warning" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                确定要注销账号吗？此操作不可恢复，所有数据将被永久删除！
            </div>
            <div class="mb-3">
                <label class="form-label">请输入密码确认</label>
                <input type="password" id="deletePassword" class="form-control" 
                       placeholder="请输入当前密码" required>
            </div>
        `, async (modal, closeModal) => {
            const passwordInput = modal.querySelector('#deletePassword');
            
            if (!passwordInput) {
                showToast('内部错误', 'error');
                return;
            }
            
            const password = passwordInput.value;

            if (!password) {
                showToast('请输入密码确认', 'error');
                return;
            }

            try {
                const publicKey = await getPublicKey();
                let encryptedPassword = password;
                if (publicKey) {
                    encryptedPassword = await PasswordCrypto.encryptPassword(password, publicKey);
                }
                await API.auth.deleteAccount(encryptedPassword);
                showToast('账号注销成功', 'success');
                setTimeout(() => {
                    localStorage.clear();
                    window.location.href = '/index.html';
                }, 1500);
            } catch (error) {
                showToast(error.message || '注销失败', 'error');
            }
        });
    }

    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        showToast('已退出登录', 'info');
        setTimeout(() => {
            window.location.href = '/index.html';
        }, 1000);
    }
}

// 页面加载完成后初始化用户菜单
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.userMenu = new UserMenu();
    });
} else {
    window.userMenu = new UserMenu();
}
