/**
 * 前端全局配置
 * 集中管理所有前端配置项，避免硬编码
 */

// API基础路径（使用相对路径，自动适配当前域名和端口）
const API_BASE = '/api';

// 应用配置
const APP_CONFIG = {
    // 版本信息
    version: '1.0.0',
    name: '测试平台',

    // API配置
    api: {
        base: API_BASE,
        timeout: 30000, // 请求超时时间（毫秒）
        retryCount: 3   // 请求失败重试次数
    },

    // 分页配置
    pagination: {
        defaultPage: 1,
        defaultPageSize: 20,
        pageSizeOptions: [10, 20, 50, 100]
    },

    // 自动刷新配置
    autoRefresh: {
        enabled: true,
        interval: 5000 // 毫秒
    },

    // 日期时间格式
    dateFormat: 'YYYY-MM-DD HH:mm:ss',
    shortDateFormat: 'MM-DD HH:mm'
};

// 导出配置（兼容不同模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API_BASE, APP_CONFIG };
}
