// Sistema de Notificações em Tempo Real com WebSocket
class RealTimeNotificationManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.userType = null;
        this.permissionGranted = false;
        this.notificationSound = null;
        this.lastNotificationId = 0;
        
        // Inicializar automaticamente
        this.init();
    }

    async init() {
        console.log('🔔 Inicializando sistema de notificações em tempo real...');
        
        // Obter tipo de usuário
        this.userType = document.body.getAttribute('data-user-type');
        
        // Só continuar se for admin ou técnico
        if (!this.userType || !['administrador', 'tecnico'].includes(this.userType)) {
            console.log('❌ Usuário não é admin/técnico - sistema desativado');
            return;
        }

        try {
            // Solicitar permissões
            await this.requestPermissions();
            
            // Configurar som
            this.setupNotificationSound();
            
            // Conectar WebSocket
            this.connectWebSocket();
            
            // Backup: polling como fallback
            this.startPollingBackup();
            
            console.log('✅ Sistema de notificações inicializado com sucesso!');
            
        } catch (error) {
            console.error('❌ Erro ao inicializar notificações:', error);
            // Fallback para sistema básico
            this.startPollingBackup();
        }
    }

    async requestPermissions() {
        if ('Notification' in window) {
            // Verificar se já temos permissão
            if (Notification.permission === 'granted') {
                this.permissionGranted = true;
                console.log('✅ Permissão para notificações já concedida');
                return;
            }
            
            // Verificar se o usuário já negou anteriormente
            if (Notification.permission === 'denied') {
                console.log('❌ Permissão negada anteriormente - não solicitará novamente');
                this.showPermissionDeniedMessage();
                return;
            }
            
            // Verificar se já perguntamos recentemente (localStorage)
            const lastAsked = localStorage.getItem('notification_permission_asked');
            const now = Date.now();
            const oneDay = 24 * 60 * 60 * 1000; // 24 horas em ms
            
            if (lastAsked && (now - parseInt(lastAsked)) < oneDay) {
                console.log('⏰ Aguardando para pedir permissão novamente (já perguntado recentemente)');
                return;
            }
            
            // Solicitar permissão
            console.log('🔔 Solicitando permissão para notificações...');
            const permission = await Notification.requestPermission();
            this.permissionGranted = permission === 'granted';
            
            // Salvar que perguntamos
            localStorage.setItem('notification_permission_asked', now.toString());
            
            if (this.permissionGranted) {
                console.log('✅ Permissão para notificações concedida');
                localStorage.setItem('notification_permission_granted', 'true');
                this.showWelcomeNotification();
            } else {
                console.warn('⚠️ Permissão para notificações negada');
                localStorage.setItem('notification_permission_granted', 'false');
                this.showPermissionDeniedMessage();
            }
        } else {
            console.warn('⚠️ Navegador não suporta notificações');
        }
    }

    showWelcomeNotification() {
        if (this.permissionGranted) {
            const notification = new Notification('Sistema de Notificações Ativo', {
                body: 'Você receberá notificações instantâneas de novos chamados',
                icon: '/static/assets/notification-icon.png',
                badge: '/static/assets/notification-icon.png',
                tag: 'welcome',
                silent: true
            });

            setTimeout(() => notification.close(), 3000);
        }
    }
    
    showPermissionDeniedMessage() {
        // Criar um aviso discreto na página
        const notice = document.createElement('div');
        notice.className = 'notification-permission-notice';
        notice.innerHTML = `
            <div class="notice-content">
                <span class="notice-icon">🔔</span>
                <span class="notice-text">Notificações desabilitadas. Para ativar, clique no ícone de sino na barra do navegador.</span>
                <button class="notice-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        document.body.appendChild(notice);
        
        // Auto-remover após 10 segundos
        setTimeout(() => {
            if (notice.parentNode) {
                notice.remove();
            }
        }, 10000);
    }

    setupNotificationSound() {
        // Criar múltiplos elementos de áudio para diferentes tipos
        this.notificationSounds = {
            newTicket: this.createAudioElement('/static/assets/notification.wav', 0.7),
            urgent: this.createAudioElement('/static/assets/notification.wav', 1.0),
            general: this.createAudioElement('/static/assets/notification.wav', 0.5)
        };
    }

    createAudioElement(src, volume) {
        const audio = new Audio(src);
        audio.volume = volume;
        audio.preload = 'auto';
        
        // Fallback para Web Audio API
        audio.onerror = () => {
            console.warn('Arquivo de áudio não encontrado, usando Web Audio API');
        };
        
        return audio;
    }

    connectWebSocket() {
        try {
            // Conectar usando Socket.IO
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('🔗 WebSocket conectado');
                this.isConnected = true;
                
                // Registrar para receber notificações
                this.socket.emit('join_notifications', {
                    user_type: this.userType
                });
                
                this.updateConnectionStatus(true);
            });

            this.socket.on('disconnect', () => {
                console.log('🔗 WebSocket desconectado');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                
                // Tentar reconectar após 5 segundos
                setTimeout(() => {
                    if (!this.isConnected) {
                        console.log('🔄 Tentando reconectar...');
                        this.socket.connect();
                    }
                }, 5000);
            });

            // Escutar novos tickets
            this.socket.on('new_ticket', (data) => {
                console.log('🎫 Novo ticket recebido via WebSocket:', data);
                this.handleNewTicketNotification(data);
            });

        } catch (error) {
            console.error('❌ Erro ao conectar WebSocket:', error);
            this.isConnected = false;
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('notification-status');
        if (statusElement) {
            statusElement.classList.toggle('connected', connected);
            statusElement.classList.toggle('disconnected', !connected);
            statusElement.title = connected ? 'Notificações em tempo real ativas' : 'Notificações offline';
        }
    }

    async handleNewTicketNotification(data) {
        try {
            // Tocar som
            this.playNotificationSound('newTicket');
            
            // Mostrar notificação do navegador
            await this.showBrowserNotification(data);
            
            // Atualizar badge
            this.updateNotificationBadge();
            
            // Mostrar toast na página (se implementado)
            this.showToastNotification(data);
            
        } catch (error) {
            console.error('❌ Erro ao processar notificação:', error);
        }
    }

    async showBrowserNotification(data) {
        if (!this.permissionGranted) return;

        const options = {
            body: `Chamado: ${data.ticket?.titulo || 'Novo chamado'}\nPrioridade: ${data.ticket?.prioridade || 'Média'}`,
            icon: '/static/assets/notification-icon.png',
            badge: '/static/assets/notification-icon.png',
            tag: `ticket-${data.ticket?.id}`,
            requireInteraction: true,
            actions: [
                {
                    action: 'view',
                    title: '👁️ Ver Chamado',
                    icon: '/static/assets/notification-icon.png'
                },
                {
                    action: 'dismiss',
                    title: '❌ Dispensar'
                }
            ],
            data: {
                ticketId: data.ticket?.id,
                url: data.ticket?.id ? `/chamado/${data.ticket.id}` : '/chamados'
            }
        };

        const notification = new Notification('🎫 Novo Chamado Aberto!', options);

        // Configurar cliques
        notification.onclick = () => {
            window.focus();
            if (data.ticket?.id) {
                window.location.href = `/chamado/${data.ticket.id}`;
            } else {
                window.location.href = '/chamados';
            }
            notification.close();
        };

        // Auto-fechar após 15 segundos
        setTimeout(() => {
            notification.close();
        }, 15000);
    }

    showToastNotification(data) {
        // Criar toast notification na página
        const toast = this.createToastElement(data);
        document.body.appendChild(toast);
        
        // Animar entrada
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Auto-remover após 8 segundos
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 8000);
    }

    createToastElement(data) {
        const toast = document.createElement('div');
        toast.className = 'notification-toast';
        toast.innerHTML = `
            <div class="toast-icon">🎫</div>
            <div class="toast-content">
                <div class="toast-title">Novo Chamado</div>
                <div class="toast-message">${data.ticket?.titulo || 'Chamado sem título'}</div>
                <div class="toast-meta">Prioridade: ${data.ticket?.prioridade || 'Média'}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        // Adicionar evento de clique
        toast.addEventListener('click', (e) => {
            if (!e.target.classList.contains('toast-close')) {
                if (data.ticket?.id) {
                    window.location.href = `/chamado/${data.ticket.id}`;
                } else {
                    window.location.href = '/chamados';
                }
            }
        });
        
        return toast;
    }

    playNotificationSound(type = 'general') {
        const sound = this.notificationSounds[type];
        if (sound) {
            sound.currentTime = 0;
            sound.play().catch(error => {
                console.warn('Não foi possível tocar som:', error);
                this.playWebAudioBeep();
            });
        } else {
            this.playWebAudioBeep();
        }
    }

    playWebAudioBeep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.1);
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.1);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.6);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.6);
            
        } catch (error) {
            console.warn('Não foi possível criar som com Web Audio API:', error);
        }
    }

    async updateNotificationBadge() {
        try {
            const response = await fetch('/api/notificacoes/nao_lidas');
            if (!response.ok) return;
            
            const data = await response.json();
            const count = data.count;
            
            const badge = document.getElementById('notification-badge');
            if (badge) {
                if (count > 0) {
                    badge.textContent = count;
                    badge.style.display = 'inline';
                    badge.classList.add('pulse');
                    
                    // Remover animação após 2 segundos
                    setTimeout(() => badge.classList.remove('pulse'), 2000);
                } else {
                    badge.style.display = 'none';
                }
            }
            
        } catch (error) {
            console.error('Erro ao atualizar badge:', error);
        }
    }

    startPollingBackup() {
        // Polling como backup quando WebSocket não está disponível
        setInterval(() => {
            if (!this.isConnected) {
                this.updateNotificationBadge();
            }
        }, 30000); // A cada 30 segundos quando offline
    }

    // Método público para reativar notificações
    async reactivateNotifications() {
        console.log('🔄 Reativando notificações...');
        
        // Limpar localStorage
        localStorage.removeItem('notification_permission_asked');
        localStorage.removeItem('notification_permission_granted');
        
        // Solicitar permissão novamente
        await this.requestPermissions();
        
        if (this.permissionGranted) {
            this.showWelcomeNotification();
            return true;
        }
        
        return false;
    }
    
    // Método público para testar
    testNotification() {
        const testData = {
            message: 'Teste de notificação',
            ticket: {
                id: 999,
                titulo: 'Chamado de Teste',
                prioridade: 'alta'
            },
            timestamp: new Date().toISOString()
        };
        
        this.handleNewTicketNotification(testData);
    }
    
    // Método público para verificar status
    getStatus() {
        return {
            permissionGranted: this.permissionGranted,
            isConnected: this.isConnected,
            userType: this.userType,
            browserSupported: 'Notification' in window,
            permission: Notification.permission
        };
    }
}

// CSS para toasts e animações
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification-toast {
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        max-width: 400px;
        transform: translateX(420px);
        transition: transform 0.3s ease;
        z-index: 10000;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .notification-toast.show {
        transform: translateX(0);
    }
    
    .toast-icon {
        font-size: 24px;
        flex-shrink: 0;
    }
    
    .toast-content {
        flex: 1;
    }
    
    .toast-title {
        font-weight: bold;
        margin-bottom: 4px;
    }
    
    .toast-message {
        font-size: 14px;
        margin-bottom: 4px;
    }
    
    .toast-meta {
        font-size: 12px;
        opacity: 0.8;
    }
    
    .toast-close {
        background: none;
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background 0.2s;
    }
    
    .toast-close:hover {
        background: rgba(255,255,255,0.2);
    }
    
    #notification-badge.pulse {
        animation: pulse-glow 1s infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { 
            transform: scale(1); 
            box-shadow: 0 0 5px rgba(220, 53, 69, 0.7);
        }
        50% { 
            transform: scale(1.1); 
            box-shadow: 0 0 15px rgba(220, 53, 69, 1);
        }
    }
    
    #notification-status {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-left: 5px;
    }
    
    #notification-status.connected {
        background-color: #28a745;
        box-shadow: 0 0 3px #28a745;
    }
    
    #notification-status.disconnected {
        background-color: #dc3545;
        box-shadow: 0 0 3px #dc3545;
    }
    
    .notification-permission-notice {
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #ffc107 0%, #ff8800 100%);
        color: #333;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 10001;
        animation: slideDown 0.3s ease;
    }
    
    .notice-content {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
    }
    
    .notice-icon {
        font-size: 20px;
    }
    
    .notice-text {
        font-size: 14px;
        font-weight: 500;
        flex: 1;
    }
    
    .notice-close {
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background 0.2s;
        color: #333;
    }
    
    .notice-close:hover {
        background: rgba(0,0,0,0.1);
    }
    
    @keyframes slideDown {
        from {
            transform: translateX(-50%) translateY(-50px);
            opacity: 0;
        }
        to {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(notificationStyles);

// Inicializar automaticamente quando a página carregar
let realTimeNotifications;

document.addEventListener('DOMContentLoaded', function() {
    realTimeNotifications = new RealTimeNotificationManager();
    
    // Expor globalmente para debug
    window.realTimeNotifications = realTimeNotifications;
    
    console.log('🚀 Sistema de notificações em tempo real carregado');
});

// Adicionar status indicator no menu de notificações
document.addEventListener('DOMContentLoaded', function() {
    const notificationLink = document.querySelector('a[href*="notificacoes"]');
    if (notificationLink) {
        const statusIndicator = document.createElement('span');
        statusIndicator.id = 'notification-status';
        statusIndicator.className = 'disconnected';
        statusIndicator.title = 'Status das notificações';
        notificationLink.appendChild(statusIndicator);
    }
});