// Tooltip 初始化脚本
// 初始化 Bootstrap 5 工具提示组件
// 在所有页面加载后调用此函数

function initTooltips() {
    // 初始化所有工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover',
            delay: { show: 200, hide: 100 }
        });
    });
    
    // 打印初始化信息（仅在开发模式）
    if (typeof console !== 'undefined' && console.log) {
        console.log(`[Tooltip Init] Initialized ${tooltipList.length} tooltips`);
    }
    
    return tooltipList;
}

// 页面加载完成后自动初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTooltips);
} else {
    // DOM 已加载，立即初始化
    initTooltips();
}
