/**
 * API调用模块
 */
const API_BASE_URL = '/api';

// 获取Token
function getToken() {
    return localStorage.getItem('token');
}

// 检查登录状态
function isLoggedIn() {
    return !!getToken();
}

// API请求封装
async function apiRequest(endpoint, options = {}) {
    const token = getToken();

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    });

    const data = await response.json();

    if (!response.ok) {
        if (response.status === 401) {
            // Token过期，跳转登录
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = 'index.html';
        }
        throw new Error(data.message || '请求失败');
    }

    return data;
}

// API方法
const API = {
    // 认证
    auth: {
        login: (username, password) => apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        }),

        register: (data) => apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        }),

        forgotPassword: (email, newPassword) => apiRequest('/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email, new_password: newPassword })
        }),

        getProfile: () => apiRequest('/auth/profile'),
        
        updateProfile: (nickname, email) => apiRequest('/auth/profile', {
            method: 'PUT',
            body: JSON.stringify({ nickname, email })
        }),
        
        changePassword: (oldPassword, newPassword) => apiRequest('/auth/password', {
            method: 'PUT',
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
        }),
        
        updateUsername: (username) => apiRequest('/auth/username', {
            method: 'PUT',
            body: JSON.stringify({ username })
        }),
        
        deleteAccount: (password) => apiRequest('/auth/account', {
            method: 'DELETE',
            body: JSON.stringify({ password })
        })
    },

    // 任务
    tasks: {
        list: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/tasks${query ? '?' + query : ''}`);
        },

        detail: (id) => apiRequest(`/tasks/${id}`),

        create: (data) => apiRequest('/tasks', {
            method: 'POST',
            body: JSON.stringify(data)
        }),

        update: (id, data) => apiRequest(`/tasks/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        }),

        delete: (id) => apiRequest(`/tasks/${id}`, {
            method: 'DELETE'
        }),

        execute: (id) => apiRequest(`/tasks/${id}/execute`, {
            method: 'POST'
        }),

        stop: (id) => apiRequest(`/tasks/${id}/stop`, {
            method: 'POST'
        }),

        statistics: () => apiRequest('/tasks/statistics')
    },

    // AI模型
    aiModels: {
        list: () => apiRequest('/ai-models'),

        create: (data) => apiRequest('/ai-models', {
            method: 'POST',
            body: JSON.stringify(data)
        }),

        update: (id, data) => apiRequest(`/ai-models/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        }),

        delete: (id) => apiRequest(`/ai-models/${id}`, {
            method: 'DELETE'
        }),

        test: (id) => apiRequest(`/ai-models/${id}/test`, {
            method: 'POST'
        }),

        preset: () => apiRequest('/ai-models/preset')
    },

    // Jenkins
    jenkins: {
        status: () => apiRequest('/integrations/jenkins/status'),

        jobs: () => apiRequest('/integrations/jenkins/jobs'),

        jobDetail: (name) => apiRequest(`/integrations/jenkins/jobs/${encodeURIComponent(name)}`),

        build: (data) => apiRequest('/integrations/jenkins/build', {
            method: 'POST',
            body: JSON.stringify(data)
        }),

        buildStatus: (name, number) => apiRequest(`/integrations/jenkins/build/${encodeURIComponent(name)}/${number}`),

        buildConsole: (name, number) => apiRequest(`/integrations/jenkins/build/${encodeURIComponent(name)}/${number}/console`)
    },

    // 禅道
    zentao: {
        status: () => apiRequest('/integrations/zentao/status'),

        products: () => apiRequest('/integrations/zentao/products'),

        cases: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/integrations/zentao/cases${query ? '?' + query : ''}`);
        },

        bugs: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/integrations/zentao/bugs${query ? '?' + query : ''}`);
        },

        createBug: (data) => apiRequest('/integrations/zentao/bugs', {
            method: 'POST',
            body: JSON.stringify(data)
        }),

        syncCases: (data) => apiRequest('/integrations/zentao/sync/cases', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    },

    // 集成
    integrations: {
        list: (type) => {
            const query = type ? `?type=${type}` : '';
            return apiRequest(`/integrations${query}`);
        },

        create: (data) => apiRequest('/integrations', {
            method: 'POST',
            body: JSON.stringify(data)
        }),

        update: (id, data) => apiRequest(`/integrations/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        }),

        delete: (id) => apiRequest(`/integrations/${id}`, {
            method: 'DELETE'
        }),

        test: (type) => apiRequest(`/integrations/${type}/test`, {
            method: 'POST'
        }),

        testById: (id) => apiRequest(`/integrations/test/${id}`, {
            method: 'POST'
        }),

        setDefault: (id) => apiRequest(`/integrations/${id}/default`, {
            method: 'POST'
        })
    },

    // 报告
    reports: {
        list: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/reports${query ? '?' + query : ''}`);
        },

        detail: (id) => apiRequest(`/reports/${id}`)
    },

    // 执行记录
    executions: {
        list: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/executions${query ? '?' + query : ''}`);
        },

        status: (executionId) => apiRequest(`/execution/${executionId}/status`),

        logs: (executionId, params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/execution/${executionId}/logs${query ? '?' + query : ''}`);
        },

        stop: (executionId) => apiRequest(`/execution/${executionId}/stop`, {
            method: 'POST'
        }),

        batchDelete: (executionIds) => apiRequest('/executions/batch-delete', {
            method: 'POST',
            body: JSON.stringify({ execution_ids: executionIds })
        })
    }
};

// 显示提示消息
let _toastTimer = null;
let _currentToast = null;

function showToast(message, type = 'success') {
    const colors = {
        success: '#52c41a',
        error: '#ff4d4f',
        warning: '#faad14',
        info: '#1890ff'
    };

    if (_currentToast && _currentToast.parentNode) {
        _currentToast.remove();
        if (_toastTimer) clearTimeout(_toastTimer);
    }

    const navbar = document.querySelector('.navbar');
    const navbarHeight = navbar ? navbar.offsetHeight + 15 : 80;

    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.style.cssText = `
        position: fixed;
        top: ${navbarHeight}px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        background: ${colors[type]};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 2147483647;
        animation: fadeInDown 0.3s ease;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);
    _currentToast = toast;

    _toastTimer = setTimeout(() => {
        toast.style.animation = 'fadeOutUp 0.3s ease';
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
            _currentToast = null;
        }, 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInDown {
        from { transform: translateX(-50%) translateY(-20px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    @keyframes fadeOutUp {
        from { transform: translateX(-50%) translateY(0); opacity: 1; }
        to { transform: translateX(-50%) translateY(-20px); opacity: 0; }
    }
`;
document.head.appendChild(style);

// 格式化时间
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const timeValue = String(dateString).trim();
    let date = new Date(timeValue);
    if (isNaN(date.getTime()) && timeValue.includes(' ')) {
        date = new Date(timeValue.replace(' ', 'T'));
    }
    if (isNaN(date.getTime())) return timeValue;
    const hasTimezone = /[+-]\d{2}:\d{2}$|Z$/.test(timeValue);
    if (!hasTimezone) {
        const offset = date.getTimezoneOffset() * 60000;
        date = new Date(date.getTime() + offset);
    }
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 获取状态文本
function getStatusText(status) {
    const texts = {
        pending: '待执行',
        running: '执行中',
        success: '成功',
        failed: '失败',
        cancelled: '已取消'
    };
    return texts[status] || status;
}

// 获取状态颜色
function getStatusColor(status) {
    const colors = {
        pending: 'secondary',
        running: 'warning',
        success: 'success',
        failed: 'danger',
        cancelled: 'secondary'
    };
    return colors[status] || 'secondary';
}

// 获取任务类型文本
function getTaskTypeText(type) {
    const texts = {
        web: 'Web测试',
        api: 'API测试',
        mobile: '移动端',
        performance: '性能测试',
        ai: 'AI测试',
        zentao: '禅道同步'
    };
    return texts[type] || type;
}

function updateRecentMonitorsDropdown() {
    const dropdown = document.getElementById('recentMonitorsDropdown');
    if (!dropdown) return;
    const recentMonitors = JSON.parse(localStorage.getItem('recent_monitors') || '[]');
    if (recentMonitors.length === 0) {
        dropdown.innerHTML = '<li><span class="dropdown-item-text text-muted small">暂无最近监控记录</span></li>';
        return;
    }
    dropdown.innerHTML = recentMonitors.slice(0, 5).map(exec => {
        const statusIcon = exec.status === 'success' ? 'bi-check-circle text-success' :
            exec.status === 'failed' ? 'bi-x-circle text-danger' : 'bi-play-circle text-primary';
        const statusText = exec.status === 'success' ? '成功' :
            exec.status === 'failed' ? '失败' : '执行中';
        return `
            <li>
                <a class="dropdown-item" href="/execution-monitor.html?execution_id=${exec.execution_id}">
                    <i class="bi ${statusIcon} me-2"></i>
                    <span>${exec.task_name || '未知任务'}</span>
                    <span class="badge bg-${exec.status === 'success' ? 'success' : exec.status === 'failed' ? 'danger' : 'primary'} ms-2">${statusText}</span>
                    <small class="text-muted d-block">${formatDateTime(exec.start_time)}</small>
                </a>
            </li>
        `;
    }).join('');
}
