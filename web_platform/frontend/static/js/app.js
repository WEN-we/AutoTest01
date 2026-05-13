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

        getProfile: () => apiRequest('/auth/profile')
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
        })
    },

    // 报告
    reports: {
        list: (params = {}) => {
            const query = new URLSearchParams(params).toString();
            return apiRequest(`/reports${query ? '?' + query : ''}`);
        },

        detail: (id) => apiRequest(`/reports/${id}`)
    }
};

// 显示提示消息
function showToast(message, type = 'success') {
    const colors = {
        success: '#52c41a',
        error: '#ff4d4f',
        warning: '#faad14',
        info: '#1890ff'
    };

    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 24px;
        background: ${colors[type]};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// 格式化时间
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
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
