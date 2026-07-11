let agentId = '';

// 获取认证头
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    const match = path.match(/\/ai-agents\/([^/]+)/);
    if (match) {
        agentId = match[1];
        loadAgentDetail();
        loadSkills();
    }

    document.getElementById('actionSelect').addEventListener('change', function() {
        document.getElementById('executeBtn').disabled = !this.value;
        updateActionParamsPlaceholder(this.value);
    });

    document.getElementById('executeBtn').addEventListener('click', executeAction);
});

// 根据选择的操作更新参数提示
function updateActionParamsPlaceholder(action) {
    const paramsTextarea = document.getElementById('actionParams');
    const placeholders = {
        'analyze_page': '{\n  "page": {\n    "url": "https://example.com",\n    "title": "示例页面"\n  }\n}',
        'generate_test_cases': '{\n  "page_analysis": {\n    "elements": [],\n    "business_logic": "用户登录流程"\n  },\n  "test_type": "functional"\n}',
        'execute_test_step': '{\n  "page": {\n    "url": "https://example.com"\n  },\n  "step": {\n    "action": "click",\n    "element": "#loginBtn",\n    "value": ""\n  }\n}',
        'execute_test_suite': '{\n  "page": {\n    "url": "https://example.com"\n  },\n  "test_cases": [\n    {\n      "id": "TC001",\n      "name": "登录测试",\n      "steps": []\n    }\n  ]\n}',
        'assert_result': '{\n  "actual": "实际结果",\n  "expected": "预期结果",\n  "assertion_type": "equal"\n}',
        'analyze_test_result': '{\n  "execution_log": {\n    "steps": [],\n    "errors": []\n  }\n}',
        'generate_test_report': '{\n  "test_results": [\n    {\n      "status": "passed",\n      "duration": 1.5\n    }\n  ],\n  "report_format": "json"\n}',
        'take_screenshot': '{\n  "page": {\n    "url": "https://example.com"\n  },\n  "name": "screenshot_1"\n}'
    };
    paramsTextarea.placeholder = placeholders[action] || '{\n  "param1": "value1"\n}';
}

async function loadAgentDetail() {
    try {
        const response = await fetch(`/api/ai-agents/${agentId}`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();

        if (result.code === 200) {
            const data = result.data;
            document.getElementById('agentId').textContent = data.agent_id;
            document.getElementById('agentName').textContent = data.name;
            document.getElementById('breadcrumbAgentName').textContent = data.name;

            const statusBadge = document.getElementById('agentStatus');
            statusBadge.textContent = getStatusText(data.status);
            statusBadge.className = `badge ${getStatusBadgeClass(data.status)}`;

            document.getElementById('createdAt').textContent = formatDate(data.created_at);
            document.getElementById('lastActive').textContent = formatDate(data.last_active);

            renderCurrentSkill(data.current_skill);
            renderStatistics(data.statistics);
        } else {
            showToast(result.message || '获取智能体信息失败', 'error');
        }
    } catch (error) {
        console.error('加载智能体详情失败:', error);
        showToast('加载智能体详情失败', 'error');
    }
}

async function loadSkills() {
    try {
        const response = await fetch(`/api/ai-agents/${agentId}/skills`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();

        if (result.code === 200) {
            renderSkillsList(result.data.skills);
        } else {
            console.error('加载技能列表失败:', result.message);
        }
    } catch (error) {
        console.error('加载技能列表失败:', error);
    }
}

function renderCurrentSkill(skillInfo) {
    const container = document.getElementById('currentSkill');

    if (!skillInfo) {
        container.innerHTML = `
            <div class="text-center py-8 text-muted">
                <i class="bi bi-person-circle fs-4 mb-2"></i>
                <p>暂无激活的角色</p>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="bg-success text-white p-3 rounded-circle me-4">
                <i class="bi bi-person-circle fs-2"></i>
            </div>
            <div class="flex-grow-1">
                <h4 class="font-bold">${skillInfo.name || '-'}</h4>
                <p class="text-muted text-sm">${skillInfo.role || '-'}</p>
                <p class="text-sm">${skillInfo.description || ''}</p>
                <div class="mt-2">
                    <span class="text-xs text-muted">核心能力:</span>
                    <div class="flex flex-wrap gap-1 mt-1">
                        ${(skillInfo.capabilities || []).slice(0, 5).map(cap =>
                            `<span class="badge bg-secondary text-white text-xs">${cap}</span>`
                        ).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderSkillsList(skills) {
    const container = document.getElementById('skillsList');

    if (!skills || skills.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center text-muted py-4">
                <i class="bi bi-inbox fs-3"></i>
                <p>暂无可用技能</p>
            </div>
        `;
        return;
    }

    container.innerHTML = skills.map(skill => `
        <div class="col-md-4 mb-3">
            <div class="card h-100 cursor-pointer" onclick="switchToSkill('${skill.skill_id || skill.id}')">
                <div class="card-body text-center">
                    <div class="bg-info text-white p-3 rounded-circle mx-auto mb-3" style="width: 60px; height: 60px;">
                        <i class="bi bi-person-circle fs-2"></i>
                    </div>
                    <h5 class="card-title">${skill.name}</h5>
                    <p class="card-text text-sm text-muted">${skill.role || ''}</p>
                    <p class="card-text text-xs text-muted mt-2 line-clamp-2">${skill.description || ''}</p>
                    <button class="btn btn-sm btn-info mt-3">切换到此角色</button>
                </div>
            </div>
        </div>
    `).join('');
}

function renderStatistics(stats) {
    if (!stats) return;

    document.getElementById('statTotal').textContent = stats.total_tests || 0;
    document.getElementById('statPassed').textContent = stats.passed || 0;
    document.getElementById('statFailed').textContent = stats.failed || 0;
    // 记忆项数从 agent 的 memory 中获取，这里显示当前 skill 名称或 '-'
    const memoryCount = stats.memory_count || (stats.current_skill ? 1 : 0);
    document.getElementById('statMemory').textContent = memoryCount;
}

async function switchToSkill(skillId) {
    try {
        const response = await fetch(`/api/ai-agents/${agentId}/skills`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ skill_id: skillId })
        });

        const result = await response.json();

        if (result.code === 200) {
            showToast(result.message, 'success');
            loadAgentDetail();
        } else {
            showToast(result.message || '切换角色失败', 'error');
        }
    } catch (error) {
        console.error('切换角色失败:', error);
        showToast('切换角色失败', 'error');
    }
}

async function executeAction() {
    const action = document.getElementById('actionSelect').value;
    const url = document.getElementById('targetUrl').value.trim();
    const paramsText = document.getElementById('actionParams').value.trim();

    let params = {};
    if (paramsText) {
        try {
            params = JSON.parse(paramsText);
        } catch {
            showToast('参数JSON格式错误，请检查JSON语法', 'warning');
            return;
        }
    }

    // 如果填写了目标URL，自动将其合并到参数中
    if (url) {
        // 对于需要 page 参数的操作，自动将 URL 包装到 page 对象中
        const pageRequiredActions = ['analyze_page', 'execute_test_step', 'execute_test_suite', 'take_screenshot'];
        if (pageRequiredActions.includes(action) && !params.page) {
            params.page = { url: url };
        } else if (!params.url) {
            params.url = url;
        }
    }

    // 验证必填参数
    const requiredParamsMap = {
        'analyze_page': ['page'],
        'generate_test_cases': ['page_analysis'],
        'execute_test_step': ['page', 'step'],
        'execute_test_suite': ['page', 'test_cases'],
        'assert_result': ['actual', 'expected'],
        'analyze_test_result': ['execution_log'],
        'generate_test_report': ['test_results'],
        'take_screenshot': ['page']
    };

    const requiredParams = requiredParamsMap[action];
    if (requiredParams) {
        const missingParams = requiredParams.filter(param => !(param in params));
        if (missingParams.length > 0) {
            showToast(`缺少必填参数: ${missingParams.join(', ')}`, 'warning');
            return;
        }
    }

    // 显示 loading 状态
    const executeBtn = document.getElementById('executeBtn');
    const originalBtnText = executeBtn.innerHTML;
    executeBtn.disabled = true;
    executeBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>执行中...';

    // 清空上次结果
    const output = document.getElementById('resultOutput');
    output.textContent = '执行中，请稍候...';
    const resultDiv = document.getElementById('executionResult');
    resultDiv.style.display = 'block';
    resultDiv.scrollIntoView({ behavior: 'smooth' });

    try {
        const response = await fetch(`/api/ai-agents/${agentId}/execute`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ action, params })
        });

        const result = await response.json();

        if (result.code === 200) {
            output.textContent = JSON.stringify(result.data, null, 2);
            showToast('操作执行成功', 'success');
        } else {
            output.textContent = JSON.stringify({
                success: false,
                error: result.message || '执行失败',
                code: result.code
            }, null, 2);
            showToast(result.message || '执行失败', 'error');
        }
    } catch (error) {
        console.error('执行操作失败:', error);
        output.textContent = JSON.stringify({
            success: false,
            error: error.message || '网络请求失败'
        }, null, 2);
        showToast('执行操作失败', 'error');
    } finally {
        // 恢复按钮状态
        executeBtn.disabled = false;
        executeBtn.innerHTML = originalBtnText;
    }
}

function getStatusText(status) {
    const statusMap = {
        'idle': '空闲',
        'running': '运行中',
        'perceiving': '感知中',
        'thinking': '思考中',
        'acting': '执行中',
        'reflecting': '反思中',
        'completed': '已完成',
        'error': '错误'
    };
    return statusMap[status] || status;
}

function getStatusBadgeClass(status) {
    const classMap = {
        'idle': 'bg-secondary',
        'running': 'bg-success',
        'perceiving': 'bg-info',
        'thinking': 'bg-info',
        'acting': 'bg-warning',
        'reflecting': 'bg-info',
        'completed': 'bg-primary',
        'error': 'bg-danger'
    };
    return classMap[status] || 'bg-secondary';
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN');
}

function showToast(message, type = 'info') {
    const toastId = 'agent-detail-toast';
    let toastEl = document.getElementById(toastId);

    if (!toastEl) {
        toastEl = document.createElement('div');
        toastEl.id = toastId;
        toastEl.className = 'toast position-fixed top-0 end-0 m-3';
        toastEl.style.zIndex = '9999';
        document.body.appendChild(toastEl);
    }

    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';

    toastEl.innerHTML = `
        <div class="toast-header ${bgClass} text-white">
            <i class="bi bi-info-circle me-2"></i>
            <strong class="me-auto">提示</strong>
            <button type="button" class="btn-close btn-close-white" onclick="document.getElementById('${toastId}').remove()"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;

    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();

    setTimeout(() => {
        toastEl.remove();
    }, 3500);
}
