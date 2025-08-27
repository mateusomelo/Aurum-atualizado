/**
 * Sistema Universal de Log - Captura TUDO que é clicável
 * Monitora todos os cliques, navegação e interações do usuário
 */

class UniversalLogger {
    constructor() {
        this.isEnabled = true;
        this.logQueue = [];
        this.batchSize = 10;
        this.batchTimeout = 5000; // 5 segundos
        this.lastBatchSent = Date.now();
        
        this.init();
    }
    
    init() {
        console.log('🎯 Universal Logger iniciado - capturando TODOS os cliques');
        
        // Aguardar DOM estar pronto
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }
        
        // Processar fila de logs periodicamente
        setInterval(() => this.processBatch(), 2000);
        
        // Log de inicialização da página
        this.logActivity('PAGE_LOAD', 'navigation', `Página carregada: ${window.location.pathname}`);
    }
    
    setupEventListeners() {
        // Capturar TODOS os cliques
        document.addEventListener('click', (e) => this.handleClick(e), true);
        
        // Capturar mudanças de foco
        document.addEventListener('focus', (e) => this.handleFocus(e), true);
        
        // Capturar submissões de formulário
        document.addEventListener('submit', (e) => this.handleSubmit(e), true);
        
        // Capturar mudanças em campos
        document.addEventListener('change', (e) => this.handleChange(e), true);
        
        // Capturar navegação
        window.addEventListener('beforeunload', () => this.handlePageLeave());
        
        // Capturar navegação por JavaScript (SPA)
        window.addEventListener('popstate', () => this.handleNavigation());
        
        // Interceptar fetch/AJAX
        this.interceptAjaxCalls();
        
        // Log específico para elementos importantes
        this.setupSpecialElements();
        
        console.log('✅ Event listeners configurados para captura universal');
    }
    
    handleClick(event) {
        const element = event.target;
        const description = this.getElementDescription(element);
        const elementType = this.getElementType(element);
        
        // Dados extras sobre o clique
        const extraData = {
            element_tag: element.tagName.toLowerCase(),
            element_id: element.id || null,
            element_class: element.className || null,
            element_text: element.textContent?.trim().substring(0, 100) || null,
            element_href: element.href || null,
            element_type: element.type || null,
            click_x: event.clientX,
            click_y: event.clientY,
            timestamp: new Date().toISOString()
        };
        
        this.logActivity('CLICK', elementType, `Clicou em: ${description}`, extraData);
        
        // Log especial para links
        if (element.tagName === 'A' && element.href) {
            this.logActivity('NAVIGATION', 'links', `Navegou para: ${element.href}`, {
                ...extraData,
                link_target: element.target || '_self'
            });
        }
    }
    
    handleFocus(event) {
        const element = event.target;
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName)) {
            const description = this.getElementDescription(element);
            
            this.logActivity('FOCUS', 'forms', `Focou em campo: ${description}`, {
                field_name: element.name || element.id || null,
                field_type: element.type || null,
                field_placeholder: element.placeholder || null
            });
        }
    }
    
    handleSubmit(event) {
        const form = event.target;
        const formData = new FormData(form);
        const fields = {};
        
        // Capturar dados do formulário (sem senhas)
        for (let [key, value] of formData.entries()) {
            if (!key.toLowerCase().includes('password') && 
                !key.toLowerCase().includes('senha')) {
                fields[key] = typeof value === 'string' ? value.substring(0, 100) : '[FILE]';
            }
        }
        
        this.logActivity('FORM_SUBMIT', 'forms', `Enviou formulário: ${form.action || form.id || 'form'}`, {
            form_action: form.action || null,
            form_method: form.method || 'GET',
            form_id: form.id || null,
            fields: fields
        });
    }
    
    handleChange(event) {
        const element = event.target;
        if (['SELECT', 'INPUT', 'TEXTAREA'].includes(element.tagName)) {
            const description = this.getElementDescription(element);
            let value = element.value;
            
            // Não logar senhas
            if (element.type === 'password' || element.name?.toLowerCase().includes('password')) {
                value = '[PASSWORD]';
            } else if (value && value.length > 50) {
                value = value.substring(0, 50) + '...';
            }
            
            this.logActivity('FIELD_CHANGE', 'forms', `Alterou campo: ${description}`, {
                field_name: element.name || element.id,
                field_type: element.type || element.tagName,
                new_value: value
            });
        }
    }
    
    handlePageLeave() {
        this.logActivity('PAGE_LEAVE', 'navigation', `Saiu da página: ${window.location.pathname}`);
        // Enviar logs restantes
        this.forceSendBatch();
    }
    
    handleNavigation() {
        this.logActivity('PAGE_NAVIGATION', 'navigation', `Navegou para: ${window.location.pathname}`);
    }
    
    interceptAjaxCalls() {
        // Interceptar fetch
        const originalFetch = window.fetch;
        window.fetch = (...args) => {
            const url = args[0];
            const options = args[1] || {};
            
            this.logActivity('AJAX_REQUEST', 'api', `Chamada AJAX: ${options.method || 'GET'} ${url}`, {
                url: url,
                method: options.method || 'GET',
                has_body: !!options.body
            });
            
            return originalFetch.apply(window, args);
        };
        
        // Interceptar XMLHttpRequest
        const originalXHR = window.XMLHttpRequest;
        window.XMLHttpRequest = function() {
            const xhr = new originalXHR();
            const originalOpen = xhr.open;
            
            xhr.open = function(method, url, ...args) {
                this._method = method;
                this._url = url;
                return originalOpen.apply(this, [method, url, ...args]);
            };
            
            xhr.addEventListener('load', function() {
                if (this._method && this._url) {
                    window.universalLogger?.logActivity('XHR_REQUEST', 'api', 
                        `XHR: ${this._method} ${this._url}`, {
                            method: this._method,
                            url: this._url,
                            status: this.status
                        });
                }
            });
            
            return xhr;
        };
    }
    
    setupSpecialElements() {
        // Observer para elementos adicionados dinamicamente
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.logActivity('DOM_CHANGE', 'ui', `Elemento adicionado: ${node.tagName}`, {
                                tag: node.tagName,
                                id: node.id,
                                className: node.className
                            });
                        }
                    });
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    getElementDescription(element) {
        // Ordem de preferência para descrição
        if (element.title) return element.title;
        if (element.alt) return element.alt;
        if (element.placeholder) return `Campo: ${element.placeholder}`;
        if (element.textContent?.trim()) return element.textContent.trim().substring(0, 50);
        if (element.id) return `#${element.id}`;
        if (element.className) return `.${element.className.split(' ')[0]}`;
        return element.tagName.toLowerCase();
    }
    
    getElementType(element) {
        const tag = element.tagName.toLowerCase();
        
        // Mapear tipos específicos
        const typeMap = {
            'a': 'links',
            'button': 'buttons', 
            'input': 'forms',
            'textarea': 'forms',
            'select': 'forms',
            'form': 'forms',
            'img': 'media',
            'video': 'media',
            'audio': 'media',
            'nav': 'navigation',
            'menu': 'navigation'
        };
        
        return typeMap[tag] || 'ui';
    }
    
    logActivity(action, module, description, extraData = null) {
        if (!this.isEnabled) return;
        
        const logEntry = {
            action: action,
            module: module,
            description: description,
            timestamp: new Date().toISOString(),
            page_url: window.location.href,
            page_title: document.title,
            user_agent: navigator.userAgent,
            screen_resolution: `${screen.width}x${screen.height}`,
            viewport_size: `${window.innerWidth}x${window.innerHeight}`,
            extra_data: extraData
        };
        
        // Adicionar à fila
        this.logQueue.push(logEntry);
        
        // Log no console para debug
        console.log('📝 Log capturado:', {
            action: action,
            module: module,
            description: description.substring(0, 100)
        });
        
        // Processar fila se necessário
        if (this.logQueue.length >= this.batchSize || 
            Date.now() - this.lastBatchSent > this.batchTimeout) {
            this.processBatch();
        }
    }
    
    processBatch() {
        if (this.logQueue.length === 0) return;
        
        const batch = this.logQueue.splice(0, this.batchSize);
        this.sendLogBatch(batch);
        this.lastBatchSent = Date.now();
    }
    
    sendLogBatch(logs) {
        fetch('/debug/log-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                logs: logs
            })
        }).then(response => {
            if (response.ok) {
                console.log(`✅ Enviados ${logs.length} logs para o servidor`);
            } else {
                console.error('❌ Erro ao enviar logs:', response.status);
                // Devolver à fila em caso de erro
                this.logQueue.unshift(...logs);
            }
        }).catch(error => {
            console.error('❌ Erro de rede ao enviar logs:', error);
            // Devolver à fila em caso de erro
            this.logQueue.unshift(...logs);
        });
    }
    
    forceSendBatch() {
        if (this.logQueue.length > 0) {
            this.sendLogBatch(this.logQueue.splice(0));
        }
    }
    
    enable() {
        this.isEnabled = true;
        console.log('✅ Universal Logger ATIVADO');
    }
    
    disable() {
        this.isEnabled = false;
        console.log('❌ Universal Logger DESATIVADO');
    }
    
    getStats() {
        return {
            enabled: this.isEnabled,
            queue_size: this.logQueue.length,
            last_batch_sent: new Date(this.lastBatchSent).toLocaleString()
        };
    }
}

// Inicializar logger global
window.universalLogger = new UniversalLogger();

// Disponibilizar controles no console
window.enableUniversalLogger = () => window.universalLogger.enable();
window.disableUniversalLogger = () => window.universalLogger.disable();
window.getLoggerStats = () => window.universalLogger.getStats();

console.log('🚀 Universal Logger carregado! Use enableUniversalLogger() ou disableUniversalLogger() para controlar.');