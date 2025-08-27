// Sistema de Notificações Simples e Confiável
class SimpleNotificationManager {
    constructor() {
        this.userType = null;
        this.permissionGranted = false;
        this.lastCount = 0;
        this.initialized = false;
        
        console.log('🔔 Iniciando sistema de notificações simples...');
        this.init();
    }

    init() {
        // Verificar tipo de usuário
        this.userType = document.body.getAttribute('data-user-type');
        console.log('Tipo de usuário:', this.userType);
        
        if (!this.userType || !['administrador', 'tecnico'].includes(this.userType)) {
            console.log('❌ Usuário não é admin/técnico - sistema desativado');
            return;
        }

        // Solicitar permissões
        this.requestNotificationPermission();
        
        // Configurar som
        this.setupSound();
        
        // Iniciar verificação
        this.startChecking();
        
        this.initialized = true;
        console.log('✅ Sistema de notificações ativo!');
        
        // Mostrar notificação de boas-vindas
        this.showWelcomeNotification();
    }

    async requestNotificationPermission() {
        if ('Notification' in window) {
            try {
                const permission = await Notification.requestPermission();
                this.permissionGranted = permission === 'granted';
                console.log('Permissão para notificações:', permission);
                
                if (!this.permissionGranted) {
                    console.warn('⚠️ Permissão para notificações negada');
                    alert('Para receber notificações de novos chamados, permita as notificações do navegador!');
                }
            } catch (error) {
                console.error('Erro ao solicitar permissão:', error);
            }
        } else {
            console.warn('⚠️ Navegador não suporta notificações');
        }
    }

    setupSound() {
        // Som simples usando Web Audio API
        this.playSound = () => {
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                // Tom de notificação agradável
                oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
                oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
                oscillator.frequency.setValueAtTime(800, audioContext.currentTime + 0.2);
                
                oscillator.type = 'sine';
                
                gainNode.gain.setValueAtTime(0, audioContext.currentTime);
                gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.1);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
                
                console.log('🔊 Som tocado!');
                
            } catch (error) {
                console.error('Erro ao tocar som:', error);
            }
        };
    }

    startChecking() {
        // Buscar contagem inicial
        this.checkNotifications();
        
        // Verificar a cada 5 segundos (mais frequente)
        setInterval(() => {
            this.checkNotifications();
        }, 5000);
        
        console.log('🔄 Verificação automática iniciada (5s)');
    }

    async checkNotifications() {
        try {
            const response = await fetch('/api/notificacoes/nao_lidas');
            if (!response.ok) {
                console.warn('Erro na API:', response.status);
                return;
            }
            
            const data = await response.json();
            const currentCount = data.count;
            
            console.log(`Notificações: ${currentCount} (anterior: ${this.lastCount})`);
            
            // Atualizar badge
            this.updateBadge(currentCount);
            
            // Se aumentou, há nova notificação
            if (currentCount > this.lastCount && this.lastCount >= 0) {
                console.log('🆕 Nova notificação detectada!');
                this.showNewNotification(currentCount);
            }
            
            this.lastCount = currentCount;
            
        } catch (error) {
            console.error('Erro ao verificar notificações:', error);
        }
    }

    updateBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline';
                badge.style.animation = 'pulse 1s';
                
                // Remover animação
                setTimeout(() => {
                    badge.style.animation = '';
                }, 1000);
            } else {
                badge.style.display = 'none';
            }
        }
    }

    showNewNotification(count) {
        // Tocar som
        if (this.playSound) {
            this.playSound();
        }
        
        // Mostrar notificação do navegador
        this.showBrowserNotification(count);
        
        // Mostrar alerta visual na página
        this.showPageAlert();
    }

    showBrowserNotification(count) {
        if (!this.permissionGranted || !('Notification' in window)) {
            console.log('❌ Notificações do navegador não disponíveis');
            return;
        }

        const options = {
            body: `Você tem ${count} notificação${count > 1 ? 'ões' : ''} não lida${count > 1 ? 's' : ''}. Clique para ver os chamados.`,
            icon: '/static/assets/notification-icon.png',
            badge: '/static/assets/notification-icon.png',
            tag: 'novo-chamado',
            requireInteraction: true,
            silent: false
        };

        const notification = new Notification('🎫 Novo Chamado!', options);

        notification.onclick = () => {
            window.focus();
            window.location.href = '/chamados';
            notification.close();
        };

        // Auto-fechar após 10 segundos
        setTimeout(() => {
            notification.close();
        }, 10000);
        
        console.log('📨 Notificação do navegador enviada');
    }

    showPageAlert() {
        // Criar alerta visual na página
        const alert = document.createElement('div');
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            z-index: 9999;
            font-weight: bold;
            cursor: pointer;
            transform: translateX(300px);
            transition: transform 0.3s ease;
            max-width: 300px;
        `;
        
        alert.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">🎫</span>
                <div>
                    <div>Novo Chamado!</div>
                    <div style="font-size: 12px; opacity: 0.9;">Clique para ver</div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" style="background:none;border:none;color:white;font-size:18px;cursor:pointer;">×</button>
            </div>
        `;
        
        alert.onclick = (e) => {
            if (e.target.tagName !== 'BUTTON') {
                window.location.href = '/chamados';
            }
        };
        
        document.body.appendChild(alert);
        
        // Animar entrada
        setTimeout(() => {
            alert.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto-remover após 8 segundos
        setTimeout(() => {
            alert.style.transform = 'translateX(300px)';
            setTimeout(() => {
                if (alert.parentElement) {
                    alert.parentElement.removeChild(alert);
                }
            }, 300);
        }, 8000);
        
        console.log('🚨 Alerta visual mostrado');
    }

    showWelcomeNotification() {
        if (this.permissionGranted && this.initialized) {
            setTimeout(() => {
                const welcomeNotification = new Notification('Sistema de Notificações Ativo', {
                    body: 'Você receberá alertas de novos chamados automaticamente!',
                    icon: '/static/assets/notification-icon.png',
                    tag: 'welcome',
                    silent: true
                });

                setTimeout(() => welcomeNotification.close(), 4000);
            }, 2000);
        }
    }

    // Método para testar
    test() {
        console.log('🧪 Testando notificações...');
        this.showNewNotification(99);
    }
}

// Inicializar quando DOM estiver pronto
let simpleNotifications;

document.addEventListener('DOMContentLoaded', function() {
    simpleNotifications = new SimpleNotificationManager();
    
    // Disponibilizar para debug
    window.simpleNotifications = simpleNotifications;
    window.testNotifications = () => simpleNotifications.test();
    
    console.log('🚀 Digite "testNotifications()" no console para testar');
});

// CSS para animações
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.2); opacity: 0.7; }
        100% { transform: scale(1); opacity: 1; }
    }
    
    #notification-badge {
        animation-duration: 1s;
        animation-timing-function: ease-in-out;
    }
`;
document.head.appendChild(style);