// Sistema de Notificações em Tempo Real com Som
class NotificationManager {
    constructor() {
        this.lastNotificationCount = 0;
        this.notificationSound = null;
        this.permissionGranted = false;
        this.isInitialized = false;
        
        // Inicializar quando a página carregar
        this.init();
    }

    async init() {
        try {
            // Solicitar permissão para notificações
            await this.requestNotificationPermission();
            
            // Preparar som de notificação
            this.setupNotificationSound();
            
            // Buscar contagem inicial
            await this.updateNotificationCount();
            
            // Iniciar polling para verificar novas notificações
            this.startPolling();
            
            this.isInitialized = true;
            console.log('Sistema de notificações inicializado');
        } catch (error) {
            console.error('Erro ao inicializar sistema de notificações:', error);
        }
    }

    async requestNotificationPermission() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            this.permissionGranted = permission === 'granted';
            
            if (!this.permissionGranted) {
                console.warn('Permissão para notificações negada');
            }
        } else {
            console.warn('Navegador não suporta notificações');
        }
    }

    setupNotificationSound() {
        // Criar elemento de áudio para o som de notificação
        this.notificationSound = new Audio('/static/assets/notification.wav');
        this.notificationSound.volume = 0.5;
        
        // Precarregar o som
        this.notificationSound.load();
        
        // Fallback para Web Audio API se o arquivo não carregar
        this.notificationSound.onerror = () => {
            console.warn('Arquivo de som não encontrado, usando Web Audio API');
            this.notificationSound = null;
        };
    }

    async updateNotificationCount() {
        try {
            const response = await fetch('/api/notificacoes/nao_lidas');
            if (!response.ok) return;
            
            const data = await response.json();
            const newCount = data.count;
            
            // Atualizar badge no menu
            this.updateNotificationBadge(newCount);
            
            // Se há novas notificações, mostrar notificação do navegador
            if (newCount > this.lastNotificationCount && this.lastNotificationCount > 0) {
                await this.showNewTicketNotification();
            }
            
            this.lastNotificationCount = newCount;
            
        } catch (error) {
            console.error('Erro ao buscar contagem de notificações:', error);
        }
    }

    updateNotificationBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline';
                badge.classList.add('animate-pulse');
            } else {
                badge.style.display = 'none';
                badge.classList.remove('animate-pulse');
            }
        }
    }

    async showNewTicketNotification() {
        // Tocar som de notificação
        this.playNotificationSound();
        
        // Mostrar notificação do navegador se permitido
        if (this.permissionGranted && 'Notification' in window) {
            const notification = new Notification('Novo Chamado Aberto', {
                body: 'Um novo chamado foi aberto no sistema. Clique para visualizar.',
                icon: '/static/assets/aurum1.png',
                badge: '/static/assets/aurum1.png',
                tag: 'novo-chamado',
                requireInteraction: true,
                actions: [
                    {
                        action: 'view',
                        title: 'Ver Chamados'
                    }
                ]
            });

            // Configurar clique na notificação
            notification.onclick = () => {
                window.focus();
                window.location.href = '/chamados';
                notification.close();
            };

            // Auto-fechar após 10 segundos
            setTimeout(() => {
                notification.close();
            }, 10000);
        }
    }

    playNotificationSound() {
        if (this.notificationSound) {
            // Reset e tocar o som do arquivo
            this.notificationSound.currentTime = 0;
            this.notificationSound.play().catch(error => {
                console.warn('Não foi possível tocar o som de notificação:', error);
                this.playWebAudioSound();
            });
        } else {
            // Usar Web Audio API como fallback
            this.playWebAudioSound();
        }
    }

    playWebAudioSound() {
        try {
            // Criar um beep usando Web Audio API
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.1);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (error) {
            console.warn('Não foi possível reproduzir som com Web Audio API:', error);
        }
    }

    startPolling() {
        // Verificar a cada 15 segundos
        setInterval(() => {
            this.updateNotificationCount();
        }, 15000);
    }

    // Método para testar notificação manualmente
    testNotification() {
        this.showNewTicketNotification();
    }
}

// Inicializar gerenciador de notificações quando a página carregar
let notificationManager;

document.addEventListener('DOMContentLoaded', function() {
    // Verificar se o usuário é admin ou técnico
    const userType = document.body.getAttribute('data-user-type');
    
    if (userType === 'administrador' || userType === 'tecnico') {
        notificationManager = new NotificationManager();
        
        // Expor globalmente para debug
        window.notificationManager = notificationManager;
    }
});

// Função para adicionar animação CSS de pulso
const style = document.createElement('style');
style.textContent = `
    .animate-pulse {
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }
    
    .notification-badge {
        background-color: #dc3545 !important;
        color: white !important;
        font-size: 0.75rem !important;
        padding: 0.25rem 0.5rem !important;
        border-radius: 50% !important;
        position: absolute !important;
        top: -8px !important;
        right: -8px !important;
        min-width: 18px !important;
        height: 18px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
`;
document.head.appendChild(style);