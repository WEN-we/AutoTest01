/**
 * 现代化主题管理器
 * 支持下拉框切换 + 精美动画效果
 */

const ThemeManager = {
    // 主题配置
    THEMES: {
        light: {
            name: '日间模式',
            desc: '明亮清爽的浅色主题',
            icon: '☀️',
            bootstrapIcon: 'bi-sun-fill'
        },
        dark: {
            name: '夜间模式',
            desc: '护眼舒适的深色主题',
            icon: '🌙',
            bootstrapIcon: 'bi-moon-stars-fill'
        },
        system: {
            name: '跟随系统',
            desc: '自动跟随系统设置切换',
            icon: '💻',
            bootstrapIcon: 'bi-display'
        }
    },
    
    // 当前状态
    currentTheme: 'system',
    isDropdownOpen: false,
    
    // 初始化
    init() {
        // 从存储读取
        this.currentTheme = localStorage.getItem('app_theme') || 'system';
        
        // 阻止 Bootstrap dropdown 冲突
        this.preventBootstrapDropdownConflict();
        
        // 应用主题
        this.applyTheme(this.currentTheme);
        
        // 初始化DOM
        this.initDropdown();
        
        // 监听系统主题变化
        this.initSystemListener();
        
        // 点击外部关闭下拉框
        this.initClickOutside();
    },
    
    // 应用主题
    applyTheme(theme) {
        let effectiveTheme = theme;
        
        if (theme === 'system') {
            effectiveTheme = this.isSystemDark() ? 'dark' : 'light';
        }
        
        // 设置data属性
        document.documentElement.setAttribute('data-theme', effectiveTheme);
        
        // 更新按钮图标
        this.updateToggleButton(theme);
        
        // 更新下拉菜单选中状态
        this.updateDropdownActive(theme);
        
        // 保存到存储
        localStorage.setItem('app_theme', theme);
        this.currentTheme = theme;
    },
    
    // 检查系统是否为深色模式
    isSystemDark() {
        return window.matchMedia && 
               window.matchMedia('(prefers-color-scheme: dark)').matches;
    },
    
    // 获取当前实际应用的主题
    getEffectiveTheme() {
        if (this.currentTheme === 'system') {
            return this.isSystemDark() ? 'dark' : 'light';
        }
        return this.currentTheme;
    },
    
    // 初始化下拉菜单
    initDropdown() {
        // 查找或创建下拉组件
        const wrappers = document.querySelectorAll('.theme-dropdown-wrapper');
        
        wrappers.forEach(wrapper => {
            // 找到切换按钮
            const toggleBtn = wrapper.querySelector('.theme-toggle-btn');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleDropdown(wrapper);
                });
            }
            
            // 找到主题选项
            const options = wrapper.querySelectorAll('.theme-option');
            options.forEach(option => {
                const theme = option.getAttribute('data-theme');
                option.addEventListener('click', () => {
                    this.applyTheme(theme);
                    this.closeDropdown(wrapper);
                });
            });
        });
        
        // 初始更新按钮和菜单状态
        this.updateToggleButton(this.currentTheme);
        this.updateDropdownActive(this.currentTheme);
    },
    
    // 切换下拉菜单
    toggleDropdown(wrapper) {
        const menu = wrapper.querySelector('.theme-dropdown-menu');
        const isOpen = menu && menu.classList.contains('show');
        
        // 先关闭所有其他下拉框
        document.querySelectorAll('.theme-dropdown-wrapper .theme-dropdown-menu.show').forEach(m => {
            const w = m.closest('.theme-dropdown-wrapper');
            if (w && w !== wrapper) {
                this.closeDropdown(w);
            }
        });
        
        // 切换当前下拉框
        if (isOpen) {
            this.closeDropdown(wrapper);
        } else {
            this.openDropdown(wrapper);
        }
    },
    
    // 打开下拉框
    openDropdown(wrapper) {
        const toggleBtn = wrapper.querySelector('.theme-toggle-btn');
        const menu = wrapper.querySelector('.theme-dropdown-menu');
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
        if (menu) menu.classList.add('show');
        wrapper.classList.add('show');
        this.isDropdownOpen = true;
    },
    
    // 关闭下拉框
    closeDropdown(wrapper) {
        const toggleBtn = wrapper.querySelector('.theme-toggle-btn');
        const menu = wrapper.querySelector('.theme-dropdown-menu');
        if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
        if (menu) menu.classList.remove('show');
        wrapper.classList.remove('show');
        this.isDropdownOpen = false;
    },
    
    // 更新切换按钮
    updateToggleButton(theme) {
        const themeConfig = this.THEMES[theme];
        
        document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
            const iconEl = btn.querySelector('.theme-icon');
            const labelEl = btn.querySelector('.theme-label');
            
            if (iconEl) {
                // 使用Bootstrap图标或emoji
                const biIcon = themeConfig.bootstrapIcon;
                iconEl.innerHTML = `<i class="bi ${biIcon}"></i>`;
            }
            
            if (labelEl) {
                labelEl.textContent = themeConfig.name;
            }
        });
    },
    
    // 更新下拉菜单选中状态
    updateDropdownActive(theme) {
        document.querySelectorAll('.theme-dropdown-wrapper').forEach(wrapper => {
            const options = wrapper.querySelectorAll('.theme-option');
            options.forEach(option => {
                const optionTheme = option.getAttribute('data-theme');
                if (optionTheme === theme) {
                    option.classList.add('active');
                } else {
                    option.classList.remove('active');
                }
            });
        });
    },
    
    // 初始化系统主题监听
    initSystemListener() {
        if (!window.matchMedia) return;
        
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        
        const listener = () => {
            if (this.currentTheme === 'system') {
                this.applyTheme('system');
            }
        };
        
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', listener);
        } else if (mediaQuery.addListener) {
            mediaQuery.addListener(listener);
        }
    },
    
    // 点击外部关闭下拉框
    initClickOutside() {
        document.addEventListener('click', (e) => {
            const wrappers = document.querySelectorAll('.theme-dropdown-wrapper');
            
            wrappers.forEach(wrapper => {
                if (!wrapper.contains(e.target)) {
                    this.closeDropdown(wrapper);
                }
            });
        });
    },
    
    // 阻止 Bootstrap dropdown 的默认行为（防止冲突）
    preventBootstrapDropdownConflict() {
        document.querySelectorAll('.theme-dropdown-wrapper .theme-toggle-btn').forEach(btn => {
            // 移除 Bootstrap 的 data-bs-toggle 属性
            btn.removeAttribute('data-bs-toggle');
        });
    },
    
    // 快速切换到日间
    setLight() {
        this.applyTheme('light');
    },
    
    // 快速切换到夜间
    setDark() {
        this.applyTheme('dark');
    },
    
    // 快速切换到跟随系统
    setSystem() {
        this.applyTheme('system');
    },
    
    // 循环切换（用于快捷操作）
    cycle() {
        const themes = ['light', 'dark', 'system'];
        const currentIndex = themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;
        this.applyTheme(themes[nextIndex]);
    }
};

// 全局导出
window.ThemeManager = ThemeManager;

// 页面加载后初始化
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
});

// 如果DOM已加载完成，立即初始化
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    ThemeManager.init();
}
