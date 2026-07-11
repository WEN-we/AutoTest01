let currentAgents = [];
let currentSkills = [];

document.addEventListener('DOMContentLoaded', function() {
    loadSkills();
    loadAgents();
});

async function loadSkills() {
    try {
        const response = await fetch('/api/ai-agents/skills');
        const result = await response.json();
        
        if (result.code === 200) {
            currentSkills = result.data.skills;
            document.getElementById('availableSkills').textContent = currentSkills.length;
        }
    } catch (error) {
        console.error('加载技能失败:', error);
    }
}

async function loadAgents() {
    try {
        const response = await fetch('/api/ai-agents');
        const result = await response.json();
        
        if (result.code === 200) {
            currentAgents = result.data.items;
            renderAgents();
            updateStats();
        }
    } catch (error) {
        console.error('加载智能体失败:', error);
        showToast('加载智能体失败', 'error');
    }
}

function renderAgents() {
    const tbody = document.getElementById('agentsTableBody');
    
    if (currentAgents.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-muted">
                    <i class="bi bi-inbox fs-1 mb-2 d-block"></i>
                    暂无智能体，请点击上方按钮创建
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = currentAgents.map(agent => `
        <tr>
            <td><code class="text-primary">${agent.agent_id}</code></td>
            <td>
                <div class="d-flex align-items-center">
                    <i class="bi bi-robot text-primary me-2"></i>
                    <strong>${agent.name}</strong>
                </div>
            </td>
            <td>
                <span class="badge bg-info">${getSkillName(agent.current_skill)}</span>
            </td>
            <td>
                <span class="badge ${getStatusBadgeClass(agent.status)}">
                    ${agent.status === 'idle' ? '空闲' : agent.status}
                </span>
            </td>
            <td>${formatDate(agent.created_at)}</td>
            <td>${formatDate(agent.last_active)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="viewAgent('${agent.agent_id}')">
                    <i class="bi bi-eye me-1"></i>详情
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="confirmDeleteAgent('${agent.agent_id}')">
                    <i class="bi bi-trash me-1"></i>删除
                </button>
            </td>
        </tr>
    `).join('');
}

function getSkillName(skillId) {
    const skillNames = {
        'test_expert': '测试专家',
        'code_helper': '代码助手',
        'report_expert': '报告专家'
    };
    return skillNames[skillId] || skillId;
}

function getStatusBadgeClass(status) {
    const classes = {
        'idle': 'bg-secondary',
        'running': 'bg-success',
        'paused': 'bg-warning',
        'completed': 'bg-primary',
        'error': 'bg-danger'
    };
    return classes[status] || 'bg-secondary';
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN');
}

function updateStats() {
    document.getElementById('totalAgents').textContent = currentAgents.length;
    document.getElementById('idleAgents').textContent = currentAgents.filter(a => a.status === 'idle').length;
    document.getElementById('activeAgents').textContent = currentAgents.filter(a => a.status !== 'idle').length;
}

function showCreateAgentModal() {
    const modal = new bootstrap.Modal(document.getElementById('createAgentModal'));
    modal.show();
}

async function createAgent() {
    const name = document.getElementById('agentName').value.trim();
    const skill = document.getElementById('agentSkill').value;
    
    if (!name) {
        showToast('请输入智能体名称', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/ai-agents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                skill: skill
            })
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showToast('智能体创建成功', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('createAgentModal'));
            modal.hide();
            loadAgents();
        } else {
            showToast(result.message || '创建失败', 'error');
        }
    } catch (error) {
        console.error('创建智能体失败:', error);
        showToast('创建智能体失败', 'error');
    }
}

function viewAgent(agentId) {
    window.location.href = `/ai-agents/${agentId}`;
}

async function confirmDeleteAgent(agentId) {
    if (confirm('确定要删除这个智能体吗？')) {
        await deleteAgent(agentId);
    }
}

async function deleteAgent(agentId) {
    try {
        const response = await fetch(`/api/ai-agents/${agentId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showToast('智能体删除成功', 'success');
            loadAgents();
        } else {
            showToast(result.message || '删除失败', 'error');
        }
    } catch (error) {
        console.error('删除智能体失败:', error);
        showToast('删除智能体失败', 'error');
    }
}

function showToast(message, type = 'info') {
    const toastId = 'ai-agent-toast';
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
