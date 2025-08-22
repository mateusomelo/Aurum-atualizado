let currentUser = null;
let users = [];
let clients = [];
let services = [];
let tickets = [];

const defaultUsers = [];

function initializeData() {
    // Limpar usuários padrão se existirem (apenas na primeira execução após alteração)
    const existingUsers = JSON.parse(localStorage.getItem('users') || '[]');
    const hasDefaultUsers = existingUsers.some(u => 
        (u.username === 'admin' && u.password === 'admin123') ||
        (u.username === 'tecnico' && u.password === 'tecnico123') ||
        (u.username === 'user' && u.password === 'user123')
    );
    
    if (hasDefaultUsers) {
        // Remove usuários padrão, mantém apenas os personalizados
        const customUsers = existingUsers.filter(u => 
            !(u.username === 'admin' && u.password === 'admin123') &&
            !(u.username === 'tecnico' && u.password === 'tecnico123') &&
            !(u.username === 'user' && u.password === 'user123')
        );
        localStorage.setItem('users', JSON.stringify(customUsers));
    } else if (!localStorage.getItem('users')) {
        localStorage.setItem('users', JSON.stringify(defaultUsers));
    }
    
    users = JSON.parse(localStorage.getItem('users')) || defaultUsers;
    clients = JSON.parse(localStorage.getItem('clients')) || [];
    services = JSON.parse(localStorage.getItem('services')) || [];
    tickets = JSON.parse(localStorage.getItem('tickets')) || [];
    
}

function saveData() {
    localStorage.setItem('users', JSON.stringify(users));
    localStorage.setItem('clients', JSON.stringify(clients));
    localStorage.setItem('services', JSON.stringify(services));
    localStorage.setItem('tickets', JSON.stringify(tickets));
}

document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    
    const user = users.find(u => u.username === username && u.password === password);
    
    if (user) {
        currentUser = user;
        document.querySelector('.login-container').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        document.getElementById('userWelcome').textContent = `Bem-vindo, ${user.name} (${user.type})`;
        
        // Aplicar classe do usuário ao body para controle de permissões
        document.body.className = `user-${user.type}`;
        
        setupUserPermissions(user.type);
        loadDashboard();
        document.getElementById('error-message').textContent = '';
    } else {
        document.getElementById('error-message').textContent = 'Usuário ou senha inválidos!';
    }
});

function setupUserPermissions(userType) {
    // Reset all permissions - ocultar tudo primeiro
    document.querySelectorAll('.admin-only').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.admin-tecnico-only').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tecnico-only').forEach(el => el.classList.remove('show'));
    document.querySelectorAll('.user-only').forEach(el => el.classList.remove('show'));
    
    // Admin: Acesso total
    if (userType === 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
        document.querySelectorAll('.admin-tecnico-only').forEach(el => el.classList.remove('hidden'));
    }
    
    // Técnico: Criar clientes, criar usuários (apenas user), responder chamados
    else if (userType === 'tecnico') {
        document.querySelectorAll('.admin-tecnico-only').forEach(el => el.classList.remove('hidden'));
        document.querySelectorAll('.tecnico-only').forEach(el => el.classList.add('show'));
    }
    
    // User: Apenas ver e criar chamados, responder chamados
    else if (userType === 'user') {
        document.querySelectorAll('.user-only').forEach(el => el.classList.add('show'));
    }
}

function logout() {
    currentUser = null;
    document.querySelector('.login-container').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('nav-users').classList.add('hidden');
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
}

function showSection(sectionId) {
    // Verificar permissões
    if (!checkSectionPermission(sectionId)) {
        alert('Você não tem permissão para acessar esta seção!');
        return;
    }
    
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    document.getElementById(sectionId).classList.add('active');
    
    switch(sectionId) {
        case 'dashboard-home':
            loadDashboard();
            break;
        case 'users':
            loadUsers();
            break;
        case 'clients':
            loadClients();
            break;
        case 'services':
            loadServices();
            break;
        case 'tickets':
            loadTickets();
            break;
    }
}

function checkSectionPermission(sectionId) {
    if (!currentUser) return false;
    
    const userType = currentUser.type;
    
    switch(sectionId) {
        case 'dashboard-home':
            return true; // Todos podem ver dashboard
        case 'users':
            return userType === 'admin'; // Apenas admin
        case 'clients':
            return userType === 'admin' || userType === 'tecnico'; // Admin e técnico
        case 'services':
            return userType === 'admin'; // Apenas admin
        case 'tickets':
            return true; // Todos podem ver chamados
        default:
            return false;
    }
}

function loadDashboard() {
    const userType = currentUser.type;
    
    if (userType === 'admin') {
        loadAdminDashboard();
    } else if (userType === 'tecnico') {
        loadTecnicoDashboard();
    } else if (userType === 'user') {
        loadUserDashboard();
    }
}

function loadAdminDashboard() {
    // Atualizar contadores
    const novosTickets = tickets.filter(t => t.status === 'aberto').length;
    const respondidosTickets = tickets.filter(t => t.status === 'andamento' || t.status === 'aguardando').length;
    const abertosTickets = tickets.filter(t => t.status !== 'fechado').length;
    const finalizadosTickets = tickets.filter(t => t.status === 'fechado').length;
    
    document.getElementById('novosCount').textContent = novosTickets;
    document.getElementById('respondidosCount').textContent = respondidosTickets;
    document.getElementById('abertosCount').textContent = abertosTickets;
    document.getElementById('finalizadosCount').textContent = finalizadosTickets;
    
    // Carregar gráficos
    loadTicketsChart();
    loadAttendanceChart();
    
    // Carregar tabela do dashboard
    loadAdminDashboardTable();
}

function loadTicketsChart() {
    const canvas = document.getElementById('ticketsChart');
    const ctx = canvas.getContext('2d');
    
    // Dados reais dos últimos 7 dias
    const dates = [];
    const ticketCounts = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        dates.push(date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }));
        
        // Contar tickets criados neste dia
        const dayStart = new Date(date);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(date);
        dayEnd.setHours(23, 59, 59, 999);
        
        const dayTickets = tickets.filter(ticket => {
            const ticketDate = new Date(ticket.date);
            return ticketDate >= dayStart && ticketDate <= dayEnd;
        }).length;
        
        ticketCounts.push(dayTickets);
    }
    
    // Limpar canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Desenhar gráfico de área
    const padding = 40;
    const chartWidth = canvas.width - (padding * 2);
    const chartHeight = canvas.height - (padding * 2);
    const maxValue = Math.max(...ticketCounts) || 5;
    
    // Desenhar grade
    ctx.strokeStyle = '#4a5568';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
    }
    
    // Desenhar área
    ctx.fillStyle = 'rgba(236, 72, 153, 0.3)';
    ctx.strokeStyle = '#ec4899';
    ctx.lineWidth = 2;
    
    ctx.beginPath();
    ctx.moveTo(padding, canvas.height - padding);
    
    ticketCounts.forEach((count, index) => {
        const x = padding + (chartWidth / (ticketCounts.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.closePath();
    ctx.fill();
    
    // Desenhar linha
    ctx.beginPath();
    ticketCounts.forEach((count, index) => {
        const x = padding + (chartWidth / (ticketCounts.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.stroke();
    
    // Desenhar pontos
    ctx.fillStyle = '#ec4899';
    ticketCounts.forEach((count, index) => {
        const x = padding + (chartWidth / (ticketCounts.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
    });
    
    // Desenhar datas
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    dates.forEach((date, index) => {
        const x = padding + (chartWidth / (dates.length - 1)) * index;
        ctx.fillText(date, x, canvas.height - 10);
    });
}

function loadAttendanceChart() {
    const canvas = document.getElementById('attendanceChart');
    const ctx = canvas.getContext('2d');
    
    // Dados reais de atendimentos dos últimos 7 dias
    const dates = [];
    const attendanceCounts = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        dates.push(date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }));
        
        // Contar tickets finalizados neste dia
        const dayStart = new Date(date);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(date);
        dayEnd.setHours(23, 59, 59, 999);
        
        const finishedTickets = tickets.filter(ticket => {
            if (ticket.status !== 'fechado') return false;
            
            // Se o ticket tem histórico de respostas, verificar a última resposta
            if (ticket.responses && ticket.responses.length > 0) {
                const lastResponse = ticket.responses[ticket.responses.length - 1];
                const responseDate = new Date(lastResponse.date);
                return responseDate >= dayStart && responseDate <= dayEnd;
            }
            
            // Se não tem respostas, usar a data de criação
            const ticketDate = new Date(ticket.date);
            return ticketDate >= dayStart && ticketDate <= dayEnd;
        }).length;
        
        attendanceCounts.push(finishedTickets);
    }
    
    // Limpar canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Desenhar gráfico de linha simples
    const padding = 40;
    const chartWidth = canvas.width - (padding * 2);
    const chartHeight = canvas.height - (padding * 2);
    const maxValue = Math.max(...attendanceCounts) || 3;
    
    // Desenhar grade
    ctx.strokeStyle = '#4a5568';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
        const y = padding + (chartHeight / 3) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
    }
    
    // Desenhar linha
    ctx.strokeStyle = '#ec4899';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    attendanceCounts.forEach((count, index) => {
        const x = padding + (chartWidth / (attendanceCounts.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.stroke();
    
    // Desenhar pontos
    ctx.fillStyle = '#ec4899';
    attendanceCounts.forEach((count, index) => {
        const x = padding + (chartWidth / (attendanceCounts.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
    });
    
    // Desenhar datas
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    dates.forEach((date, index) => {
        const x = padding + (chartWidth / (dates.length - 1)) * index;
        ctx.fillText(date, x, canvas.height - 10);
    });
}

function loadAdminDashboardTable() {
    const tbody = document.querySelector('#adminDashboardTable tbody');
    tbody.innerHTML = '';
    
    tickets.forEach(ticket => {
        const client = clients.find(c => c.id === ticket.clientId);
        const service = services.find(s => s.id === ticket.serviceId);
        const attendant = ticket.attendantId ? users.find(u => u.id === ticket.attendantId) : null;
        const ticketDate = new Date(ticket.date);
        const formattedDateTime = `${ticketDate.toLocaleDateString()} ${ticketDate.toLocaleTimeString()}`;
        
        // Calcular deadline (exemplo: 24h após criação)
        const deadline = new Date(ticket.date);
        deadline.setHours(deadline.getHours() + 24);
        const formattedDeadline = `${deadline.toLocaleDateString()} ${deadline.toLocaleTimeString()}`;
        
        // Status SLA (simulado)
        const now = new Date();
        const slaStatus = now > deadline ? 'Vencido' : 'No prazo';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>#${ticket.id}</td>
            <td>${ticket.title}</td>
            <td>${service ? service.category : 'N/A'}</td>
            <td>${client ? client.name : 'N/A'}</td>
            <td>${client ? (client.company || client.name) : 'N/A'}</td>
            <td>${service ? service.name : 'N/A'}</td>
            <td>${formattedDateTime}</td>
            <td>${formattedDeadline}</td>
            <td><span class="status-${ticket.status}">${ticket.status}</span></td>
            <td><span class="priority-${ticket.priority}">${ticket.priority}</span></td>
            <td>${attendant ? attendant.name : 'Não atribuído'}</td>
            <td><span class="${slaStatus === 'Vencido' ? 'sla-expired' : 'sla-ok'}">${slaStatus}</span></td>
        `;
        
        // Adicionar evento de clique para abrir modal detalhado
        row.addEventListener('click', () => {
            editTicket(ticket.id);
        });
        row.style.cursor = 'pointer';
        
        tbody.appendChild(row);
    });
}

function loadTecnicoDashboard() {
    // Atualizar contadores
    const novosTickets = tickets.filter(t => t.status === 'aberto').length;
    const respondidosTickets = tickets.filter(t => t.status === 'andamento' || t.status === 'aguardando').length;
    const abertosTickets = tickets.filter(t => t.status !== 'fechado').length;
    const finalizadosTickets = tickets.filter(t => t.status === 'fechado').length;
    
    document.getElementById('novosCountTec').textContent = novosTickets;
    document.getElementById('respondidosCountTec').textContent = respondidosTickets;
    document.getElementById('abertosCountTec').textContent = abertosTickets;
    document.getElementById('finalizadosCountTec').textContent = finalizadosTickets;
    
    // Carregar gráficos para técnico
    loadTicketsChartTecnico();
    loadAttendanceChartTecnico();
    
    // Carregar tabela do dashboard para técnico
    loadTecnicoDashboardTable();
}

function loadUserDashboard() {
    // Filtrar chamados do usuário (se estiver vinculado a um cliente)
    let userTickets = tickets;
    if (currentUser.clientId) {
        userTickets = tickets.filter(t => t.clientId === currentUser.clientId);
    }
    
    document.getElementById('myTickets').textContent = userTickets.length;
    document.getElementById('myOpenTickets').textContent = userTickets.filter(t => t.status !== 'fechado').length;
    document.getElementById('myFinishedTickets').textContent = userTickets.filter(t => t.status === 'fechado').length;
    
    // Último chamado
    if (userTickets.length > 0) {
        const lastTicket = userTickets.sort((a, b) => new Date(b.date) - new Date(a.date))[0];
        document.getElementById('lastTicketDate').textContent = new Date(lastTicket.date).toLocaleDateString();
    } else {
        document.getElementById('lastTicketDate').textContent = '-';
    }
    
    // Carregar lista de chamados
    loadUserTicketsList(userTickets);
}

function loadUserTicketsList(userTickets) {
    const ticketsList = document.getElementById('userTicketsList');
    loadTicketsList(ticketsList, userTickets, 'Nenhum chamado encontrado. Clique em "Novo Chamado" para criar seu primeiro chamado.');
}

function loadAdminTicketsList() {
    const ticketsList = document.getElementById('adminTicketsList');
    // Admin vê os 10 chamados mais recentes
    const recentTickets = tickets.slice(0, 10);
    loadTicketsList(ticketsList, recentTickets, 'Nenhum chamado encontrado. Clique em "Novo Chamado" para criar o primeiro chamado.');
}

function loadTecnicoTicketsList() {
    const ticketsList = document.getElementById('tecnicoTicketsList');
    // Técnico vê os 10 chamados mais recentes
    const recentTickets = tickets.slice(0, 10);
    loadTicketsList(ticketsList, recentTickets, 'Nenhum chamado encontrado. Clique em "Novo Chamado" para criar o primeiro chamado.');
}

function loadTicketsList(container, ticketsArray, emptyMessage) {
    container.innerHTML = '';
    
    if (ticketsArray.length === 0) {
        container.innerHTML = `<div class="empty-tickets">${emptyMessage}</div>`;
        return;
    }
    
    // Ordenar por data (mais recentes primeiro)
    const sortedTickets = ticketsArray.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    sortedTickets.forEach(ticket => {
        const client = clients.find(c => c.id === ticket.clientId);
        const service = services.find(s => s.id === ticket.serviceId);
        const attendant = ticket.attendantId ? users.find(u => u.id === ticket.attendantId) : null;
        
        const ticketCard = document.createElement('div');
        ticketCard.className = 'ticket-card';
        
        // Visualização simplificada para admin/técnico
        if (currentUser.type === 'admin' || currentUser.type === 'tecnico') {
            const ticketDate = new Date(ticket.date);
            const formattedDateTime = `${ticketDate.toLocaleDateString()} ${ticketDate.toLocaleTimeString()}`;
            
            ticketCard.innerHTML = `
                <div class="ticket-header">
                    <h4 class="ticket-title">${ticket.title}</h4>
                    <span class="ticket-id">#${ticket.id}</span>
                </div>
                
                <div class="ticket-info-simple">
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Nome:</span> ${ticket.createdByName || 'N/A'}
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Cliente:</span> ${client ? client.name : 'N/A'}
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Serviço:</span> ${service ? service.name : 'N/A'}
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Data/Hora:</span> ${formattedDateTime}
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Atendente:</span> ${attendant ? `${attendant.name}` : 'Não atribuído'}
                    </div>
                </div>
                
                <div class="ticket-actions">
                    <button onclick="editTicket(${ticket.id})" class="btn-primary">Editar</button>
                    ${(currentUser.type === 'admin' || currentUser.type === 'tecnico') ? `<button onclick="deleteTicket(${ticket.id})" style="background: #e74c3c;">Excluir</button>` : ''}
                </div>
            `;
        } else {
            // Visualização completa para users
            ticketCard.innerHTML = `
                <div class="ticket-header">
                    <h4 class="ticket-title">${ticket.title}</h4>
                    <span class="ticket-id">#${ticket.id}</span>
                </div>
                
                <div class="ticket-info">
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Criado por:</span> ${ticket.createdByName || 'N/A'}
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Cliente:</span> ${client ? client.name : 'N/A'}
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Prioridade:</span> 
                        <span class="priority-${ticket.priority}">${ticket.priority}</span>
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Atendente:</span> ${attendant ? `${attendant.name} (${attendant.type})` : 'Não atribuído'}
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Status:</span> 
                        <span class="status-${ticket.status}">${ticket.status}</span>
                    </div>
                    <div class="ticket-info-item">
                        <span class="ticket-info-label">Serviço:</span> ${service ? service.name : 'N/A'}
                    </div>
                </div>
                
                <div class="ticket-description">
                    ${ticket.description}
                </div>
                
                <div class="ticket-info-item">
                    <span class="ticket-info-label">Data:</span> ${new Date(ticket.date).toLocaleDateString()}
                </div>
                
                <div class="ticket-actions">
                    <button onclick="editTicket(${ticket.id})" class="btn-primary">Responder</button>
                </div>
            `;
        }
        
        container.appendChild(ticketCard);
    });
}

function loadUsers() {
    if (currentUser.type !== 'admin' && currentUser.type !== 'tecnico') return;
    
    const tbody = document.querySelector('#usersTable tbody');
    tbody.innerHTML = '';
    
    // Filtrar usuários baseado no tipo do usuário atual
    const filteredUsers = currentUser.type === 'admin' ? 
        users : 
        users.filter(u => u.type === 'user'); // Técnicos veem apenas clientes
    
    filteredUsers.forEach(user => {
        const row = document.createElement('tr');
        const canDelete = currentUser.type === 'admin';
        const canEdit = currentUser.type === 'admin' || 
                       (currentUser.type === 'tecnico' && user.type === 'user');
        
        // Encontrar cliente vinculado
        const linkedClient = user.clientId ? clients.find(c => c.id === user.clientId) : null;
        const clientName = linkedClient ? linkedClient.name : '-';
        
        row.innerHTML = `
            <td>${user.id}</td>
            <td>${user.name}</td>
            <td>${user.username}</td>
            <td>${user.type}</td>
            <td>${clientName}</td>
            <td>
                <button onclick="editUser(${user.id})" ${!canEdit ? 'disabled' : ''}>Editar</button>
                <button onclick="deleteUser(${user.id})" ${!canDelete ? 'disabled' : ''}>Excluir</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function loadClients() {
    const tbody = document.querySelector('#clientsModernTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    const canManageClients = currentUser.type === 'admin' || currentUser.type === 'tecnico';
    
    clients.forEach(client => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" class="client-checkbox" data-client-id="${client.id}">
            </td>
            <td>
                <span class="client-name">${client.name}</span>
                <br>
                <small style="color: #a0aec0;">${client.email}</small>
            </td>
            <td>
                <span class="organization-badge">${client.name}</span>
            </td>
            <td style="color: #a0aec0;">
                ${client.phone || '-'}
            </td>
            <td>
                <div class="mais-btn" onclick="toggleMaisDropdown(event, ${client.id})" ${!canManageClients ? 'style="display:none"' : ''}>
                    Mais ▼
                    <div class="mais-dropdown" id="dropdown-${client.id}">
                        <div class="mais-dropdown-item" onclick="editClient(${client.id})">✏️ Editar</div>
                        <div class="mais-dropdown-item" onclick="deleteClient(${client.id})">🗑️ Excluir</div>
                        <div class="mais-dropdown-item" onclick="viewClientDetails(${client.id})">👁️ Visualizar</div>
                    </div>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function showClientsView(view) {
    // Atualizar navegação ativa
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.nav-item').classList.add('active');
    
    // Atualizar título
    const title = document.querySelector('.clients-header h2');
    if (view === 'clientes') {
        title.textContent = 'Clientes';
        loadClients();
    }
}

function loadOrganizations() {
    const tbody = document.querySelector('#clientsModernTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    // Agrupar clientes por organização
    const organizations = {};
    clients.forEach(client => {
        const org = client.company || client.name;
        if (!organizations[org]) {
            organizations[org] = [];
        }
        organizations[org].push(client);
    });
    
    Object.keys(organizations).forEach(orgName => {
        const clientsInOrg = organizations[orgName];
        const mainClient = clientsInOrg[0];
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" class="client-checkbox" data-org="${orgName}">
            </td>
            <td>
                <span class="client-name">${orgName}</span>
                <br>
                <small style="color: #a0aec0;">${clientsInOrg.length} cliente(s)</small>
            </td>
            <td>
                <span class="organization-badge">${orgName}</span>
            </td>
            <td style="color: #a0aec0;">
                ${mainClient.phone || '-'}
            </td>
            <td>
                <div class="mais-btn" onclick="toggleMaisDropdown(event, 'org-${orgName}')">
                    Mais ▼
                    <div class="mais-dropdown" id="dropdown-org-${orgName}">
                        <div class="mais-dropdown-item" onclick="viewOrgDetails('${orgName}')">👁️ Ver Clientes</div>
                        <div class="mais-dropdown-item" onclick="editOrganization('${orgName}')">✏️ Editar</div>
                    </div>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function toggleMaisDropdown(event, id) {
    event.stopPropagation();
    
    // Fechar outros dropdowns
    document.querySelectorAll('.mais-dropdown').forEach(dropdown => {
        dropdown.classList.remove('show');
    });
    
    // Abrir o dropdown clicado
    const dropdown = document.getElementById(`dropdown-${id}`);
    if (dropdown) {
        dropdown.classList.add('show');
    }
}

function viewClientDetails(clientId) {
    const client = clients.find(c => c.id === clientId);
    alert(`Detalhes do cliente:\nNome: ${client.name}\nEmail: ${client.email}\nTelefone: ${client.phone || 'N/A'}\nEmpresa: ${client.company || 'N/A'}`);
}

function viewOrgDetails(orgName) {
    const orgClients = clients.filter(c => (c.company || c.name) === orgName);
    const clientsList = orgClients.map(c => `• ${c.name} (${c.email})`).join('\n');
    alert(`Clientes da organização ${orgName}:\n\n${clientsList}`);
}

function editOrganization(orgName) {
    alert(`Edição de organização ${orgName} será implementada`);
}

// Funções para gráficos do técnico
function loadTicketsChartTecnico() {
    const canvas = document.getElementById('ticketsChartTec');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Dados reais dos últimos 7 dias
    const dates = [];
    const ticketCounts = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        dates.push(date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }));
        
        // Contar tickets criados neste dia
        const dayStart = new Date(date);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(date);
        dayEnd.setHours(23, 59, 59, 999);
        
        const dayTickets = tickets.filter(ticket => {
            const ticketDate = new Date(ticket.date);
            return ticketDate >= dayStart && ticketDate <= dayEnd;
        }).length;
        
        ticketCounts.push(dayTickets);
    }
    
    // Desenhar gráfico usando a mesma lógica do admin
    drawAreaChart(ctx, canvas, dates, ticketCounts);
}

function loadAttendanceChartTecnico() {
    const canvas = document.getElementById('attendanceChartTec');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Dados reais de atendimentos dos últimos 7 dias
    const dates = [];
    const attendanceCounts = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        dates.push(date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }));
        
        // Contar tickets finalizados neste dia
        const dayStart = new Date(date);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(date);
        dayEnd.setHours(23, 59, 59, 999);
        
        const finishedTickets = tickets.filter(ticket => {
            if (ticket.status !== 'fechado') return false;
            
            if (ticket.responses && ticket.responses.length > 0) {
                const lastResponse = ticket.responses[ticket.responses.length - 1];
                const responseDate = new Date(lastResponse.date);
                return responseDate >= dayStart && responseDate <= dayEnd;
            }
            
            const ticketDate = new Date(ticket.date);
            return ticketDate >= dayStart && ticketDate <= dayEnd;
        }).length;
        
        attendanceCounts.push(finishedTickets);
    }
    
    // Desenhar gráfico usando a mesma lógica do admin
    drawLineChart(ctx, canvas, dates, attendanceCounts);
}

function loadTecnicoDashboardTable() {
    const tbody = document.querySelector('#tecnicoDashboardTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    tickets.forEach(ticket => {
        const client = clients.find(c => c.id === ticket.clientId);
        const service = services.find(s => s.id === ticket.serviceId);
        const attendant = ticket.attendantId ? users.find(u => u.id === ticket.attendantId) : null;
        const ticketDate = new Date(ticket.date);
        const formattedDateTime = `${ticketDate.toLocaleDateString()} ${ticketDate.toLocaleTimeString()}`;
        
        // Calcular deadline (exemplo: 24h após criação)
        const deadline = new Date(ticket.date);
        deadline.setHours(deadline.getHours() + 24);
        const formattedDeadline = `${deadline.toLocaleDateString()} ${deadline.toLocaleTimeString()}`;
        
        // Status SLA (simulado)
        const now = new Date();
        const slaStatus = now > deadline ? 'Vencido' : 'No prazo';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>#${ticket.id}</td>
            <td>${ticket.title}</td>
            <td>${service ? service.category : 'N/A'}</td>
            <td>${client ? client.name : 'N/A'}</td>
            <td>${client ? (client.company || client.name) : 'N/A'}</td>
            <td>${service ? service.name : 'N/A'}</td>
            <td>${formattedDateTime}</td>
            <td>${formattedDeadline}</td>
            <td><span class="status-${ticket.status}">${ticket.status}</span></td>
            <td><span class="priority-${ticket.priority}">${ticket.priority}</span></td>
            <td>${attendant ? attendant.name : 'Não atribuído'}</td>
            <td><span class="${slaStatus === 'Vencido' ? 'sla-expired' : 'sla-ok'}">${slaStatus}</span></td>
        `;
        
        // Adicionar evento de clique para abrir modal detalhado
        row.addEventListener('click', () => {
            editTicket(ticket.id);
        });
        row.style.cursor = 'pointer';
        
        tbody.appendChild(row);
    });
}

// Função auxiliar para desenhar gráfico de área
function drawAreaChart(ctx, canvas, dates, data) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const padding = 40;
    const chartWidth = canvas.width - (padding * 2);
    const chartHeight = canvas.height - (padding * 2);
    const maxValue = Math.max(...data) || 5;
    
    // Desenhar grade
    ctx.strokeStyle = '#4a5568';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
    }
    
    // Desenhar área
    ctx.fillStyle = 'rgba(236, 72, 153, 0.3)';
    ctx.strokeStyle = '#ec4899';
    ctx.lineWidth = 2;
    
    ctx.beginPath();
    ctx.moveTo(padding, canvas.height - padding);
    
    data.forEach((count, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.closePath();
    ctx.fill();
    
    // Desenhar linha
    ctx.beginPath();
    data.forEach((count, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.stroke();
    
    // Desenhar pontos
    ctx.fillStyle = '#ec4899';
    data.forEach((count, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
    });
    
    // Desenhar datas
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    dates.forEach((date, index) => {
        const x = padding + (chartWidth / (dates.length - 1)) * index;
        ctx.fillText(date, x, canvas.height - 10);
    });
}

// Função auxiliar para desenhar gráfico de linha
function drawLineChart(ctx, canvas, dates, data) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const padding = 40;
    const chartWidth = canvas.width - (padding * 2);
    const chartHeight = canvas.height - (padding * 2);
    const maxValue = Math.max(...data) || 3;
    
    // Desenhar grade
    ctx.strokeStyle = '#4a5568';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
        const y = padding + (chartHeight / 3) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
    }
    
    // Desenhar linha
    ctx.strokeStyle = '#ec4899';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    data.forEach((count, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.stroke();
    
    // Desenhar pontos
    ctx.fillStyle = '#ec4899';
    data.forEach((count, index) => {
        const x = padding + (chartWidth / (data.length - 1)) * index;
        const y = canvas.height - padding - (count / maxValue) * chartHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
    });
    
    // Desenhar datas
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    dates.forEach((date, index) => {
        const x = padding + (chartWidth / (dates.length - 1)) * index;
        ctx.fillText(date, x, canvas.height - 10);
    });
}

// Fechar dropdowns ao clicar fora
document.addEventListener('click', function() {
    document.querySelectorAll('.mais-dropdown').forEach(dropdown => {
        dropdown.classList.remove('show');
    });
});

function loadServices() {
    const tbody = document.querySelector('#servicesTable tbody');
    tbody.innerHTML = '';
    
    const canManageServices = currentUser.type === 'admin';
    
    services.forEach(service => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${service.id}</td>
            <td>${service.name}</td>
            <td>${service.description}</td>
            <td>${service.category}</td>
            <td>
                <button onclick="editService(${service.id})" ${!canManageServices ? 'disabled' : ''}>Editar</button>
                <button onclick="deleteService(${service.id})" ${!canManageServices ? 'disabled' : ''}>Excluir</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function loadTickets() {
    const tbody = document.querySelector('#ticketsTable tbody');
    tbody.innerHTML = '';
    
    const canEditTickets = currentUser.type === 'admin' || currentUser.type === 'tecnico';
    const canDeleteTickets = currentUser.type === 'admin';
    
    tickets.forEach(ticket => {
        const client = clients.find(c => c.id === ticket.clientId);
        const service = services.find(s => s.id === ticket.serviceId);
        const attendant = ticket.attendantId ? users.find(u => u.id === ticket.attendantId) : null;
        const ticketDate = new Date(ticket.date);
        const formattedDateTime = `${ticketDate.toLocaleDateString()} ${ticketDate.toLocaleTimeString()}`;
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ticket.id}</td>
            <td>${ticket.createdByName || 'N/A'}</td>
            <td>${ticket.title}</td>
            <td>${client ? client.name : 'N/A'}</td>
            <td>${service ? service.name : 'N/A'}</td>
            <td>${formattedDateTime}</td>
            <td>${attendant ? `${attendant.name}` : 'Não atribuído'}</td>
            <td>
                <button onclick="editTicket(${ticket.id})" ${!canEditTickets ? 'disabled' : ''}>Editar</button>
                <button onclick="deleteTicket(${ticket.id})" ${!canDeleteTickets ? 'disabled' : ''}>Excluir</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function showUserModal() {
    // Admin: pode criar qualquer tipo de usuário
    // Técnico: pode criar apenas usuários do tipo 'user'
    if (currentUser.type !== 'admin' && currentUser.type !== 'tecnico') {
        alert('Você não tem permissão para criar usuários!');
        return;
    }
    
    document.getElementById('userModal').style.display = 'block';
    document.getElementById('userForm').reset();
    document.getElementById('editUserId').value = '';
    
    // Limpar campos explicitamente
    document.getElementById('userName').value = '';
    document.getElementById('userUsername').value = '';
    document.getElementById('userPassword').value = '';
    document.getElementById('userClient').value = '';
    
    // Se for técnico, limitar opções de tipo de usuário
    const userTypeSelect = document.getElementById('userType');
    if (currentUser.type === 'tecnico') {
        userTypeSelect.innerHTML = '<option value="user">Usuário</option>';
        userTypeSelect.disabled = true;
    } else {
        userTypeSelect.innerHTML = `
            <option value="user">Usuário</option>
            <option value="tecnico">Técnico</option>
            <option value="admin">Administrador</option>
        `;
        userTypeSelect.disabled = false;
    }
    
    // Popular lista de clientes
    const userClientSelect = document.getElementById('userClient');
    userClientSelect.innerHTML = '<option value="">Nenhum cliente</option>';
    clients.forEach(client => {
        userClientSelect.innerHTML += `<option value="${client.id}">${client.name}</option>`;
    });
}

function showClientModal() {
    if (currentUser.type !== 'admin' && currentUser.type !== 'tecnico') {
        alert('Você não tem permissão para criar clientes!');
        return;
    }
    
    document.getElementById('clientModal').style.display = 'block';
    document.getElementById('clientForm').reset();
    document.getElementById('editClientId').value = '';
    
    // Limpar campos explicitamente
    document.getElementById('clientName').value = '';
    document.getElementById('clientEmail').value = '';
    document.getElementById('clientPhone').value = '';
    document.getElementById('clientCompany').value = '';
}

function showServiceModal() {
    if (currentUser.type !== 'admin') {
        alert('Você não tem permissão para criar serviços!');
        return;
    }
    
    document.getElementById('serviceModal').style.display = 'block';
    document.getElementById('serviceForm').reset();
    document.getElementById('editServiceId').value = '';
    
    // Limpar campos explicitamente
    document.getElementById('serviceName').value = '';
    document.getElementById('serviceDescription').value = '';
}

function showTicketModal(ticket = null) {
    const clientSelect = document.getElementById('ticketClient');
    const serviceSelect = document.getElementById('ticketService');
    const attendantSelect = document.getElementById('ticketAttendant');
    
    // Popular clientes
    clientSelect.innerHTML = '<option value="">Selecione um cliente</option>';
    clients.forEach(client => {
        clientSelect.innerHTML += `<option value="${client.id}">${client.name}</option>`;
    });
    
    // Adicionar evento para preencher email automaticamente
    clientSelect.onchange = function() {
        const selectedClientId = parseInt(this.value);
        const selectedClient = clients.find(c => c.id === selectedClientId);
        const emailField = document.getElementById('ticketEmail');
        
        if (selectedClient && selectedClient.email) {
            emailField.value = selectedClient.email;
        } else {
            emailField.value = '';
        }
    };
    
    // Popular serviços
    serviceSelect.innerHTML = '<option value="">Selecione um serviço</option>';
    services.forEach(service => {
        serviceSelect.innerHTML += `<option value="${service.id}">${service.name}</option>`;
    });
    
    // Popular lista de atendentes (apenas admin e técnico)
    attendantSelect.innerHTML = '<option value="">Selecione um atendente</option>';
    const attendants = users.filter(user => user.type === 'admin' || user.type === 'tecnico');
    attendants.forEach(attendant => {
        attendantSelect.innerHTML += `<option value="${attendant.id}">${attendant.name} (${attendant.type})</option>`;
    });
    
    // Resetar modo de edição
    document.body.classList.remove('ticket-edit-mode');
    
    if (ticket) {
        // Modo visualização - preencher dados do chamado
        document.getElementById('editTicketId').value = ticket.id;
        document.getElementById('ticketTitle').textContent = `Vincular Chamado: #${ticket.id} - ${ticket.title || 'chamado'}`;
        document.getElementById('ticketDescription').value = ticket.description || '';
        document.getElementById('ticketPriority').value = ticket.priority || 'media';
        document.getElementById('ticketClient').value = ticket.clientId || '';
        document.getElementById('ticketService').value = ticket.serviceId || '';
        document.getElementById('ticketAttendant').value = ticket.attendantId || '';
        document.getElementById('ticketStatus').value = ticket.status || 'aberto';
        
        // Popular email do ticket ou do cliente
        const client = clients.find(c => c.id === ticket.clientId);
        document.getElementById('ticketEmail').value = ticket.email || (client ? client.email : '') || '';
        
        // Mostrar seção de respostas
        // Admin e técnicos sempre veem, usuários veem apenas se for seu chamado
        if (currentUser.type === 'admin' || currentUser.type === 'tecnico' || 
           (currentUser.type === 'user' && ticket.clientId === currentUser.clientId)) {
            document.getElementById('ticketResponsesSection').style.display = 'block';
            if (ticket.responses) {
                loadTicketResponses(ticket);
            }
        } else {
            document.getElementById('ticketResponsesSection').style.display = 'none';
        }
        
        // Configurar campos como readonly inicialmente
        setTicketFieldsReadonly(true);
        
        // Mostrar botão "Mais" baseado em permissões
        if (currentUser.type === 'admin' || currentUser.type === 'tecnico') {
            document.getElementById('ticketMaisContainer').style.display = 'inline-block';
            console.log('Botão Mais mostrado para:', currentUser.type);
        } else {
            document.getElementById('ticketMaisContainer').style.display = 'none';
            console.log('Botão Mais oculto para:', currentUser.type);
        }
    } else {
        // Modo criação
        document.getElementById('ticketTitle').textContent = 'Novo Chamado';
        document.getElementById('ticketForm').reset();
        document.getElementById('editTicketId').value = '';
        document.getElementById('ticketResponsesSection').style.display = 'none';
        document.getElementById('ticketMaisContainer').style.display = 'none';
        
        // Garantir que campos iniciem vazios
        document.getElementById('ticketDescription').value = '';
        document.getElementById('ticketPriority').value = '';
        document.getElementById('ticketEmail').value = '';
        
        // Campos liberados para criação
        setTicketFieldsReadonly(false);
        
        // Se for usuário comum e estiver vinculado a um cliente
        if (currentUser.type === 'user' && currentUser.clientId) {
            clientSelect.value = currentUser.clientId;
            // Preencher email automaticamente
            const client = clients.find(c => c.id === currentUser.clientId);
            if (client && client.email) {
                document.getElementById('ticketEmail').value = client.email;
            }
        }
    }
    
    document.getElementById('ticketModal').style.display = 'block';
    
    // Aplicar restrições para usuários comuns
    if (currentUser.type === 'user') {
        // Usuários comuns não podem alterar cliente, status ou atendente
        const clientGroup = document.querySelector('#ticketClient').closest('.input-group');
        const statusGroup = document.querySelector('#ticketStatus').closest('.input-group');
        const attendantGroup = document.querySelector('#ticketAttendant').closest('.input-group');
        
        if (clientGroup) clientGroup.style.display = 'none';
        if (statusGroup) statusGroup.style.display = 'none'; 
        if (attendantGroup) attendantGroup.style.display = 'none';
        
        if (currentUser.clientId) {
            clientSelect.value = currentUser.clientId;
            document.getElementById('ticketStatus').value = 'aberto';
        }
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

document.getElementById('userForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const id = document.getElementById('editUserId').value;
    const name = document.getElementById('userName').value;
    const username = document.getElementById('userUsername').value;
    const password = document.getElementById('userPassword').value;
    const type = document.getElementById('userType').value;
    const clientId = document.getElementById('userClient').value || null;
    
    if (id) {
        const userIndex = users.findIndex(u => u.id == id);
        users[userIndex] = { id: parseInt(id), name, username, password, type, clientId: clientId ? parseInt(clientId) : null };
    } else {
        const newId = Math.max(...users.map(u => u.id)) + 1;
        users.push({ id: newId, name, username, password, type, clientId: clientId ? parseInt(clientId) : null });
    }
    
    saveData();
    loadUsers();
    closeModal('userModal');
});

document.getElementById('clientForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const id = document.getElementById('editClientId').value;
    const name = document.getElementById('clientName').value;
    const email = document.getElementById('clientEmail').value;
    const phone = document.getElementById('clientPhone').value;
    const company = document.getElementById('clientCompany').value;
    
    if (id) {
        const clientIndex = clients.findIndex(c => c.id == id);
        clients[clientIndex] = { id: parseInt(id), name, email, phone, company };
    } else {
        const newId = clients.length > 0 ? Math.max(...clients.map(c => c.id)) + 1 : 1;
        clients.push({ id: newId, name, email, phone, company });
    }
    
    saveData();
    loadClients();
    closeModal('clientModal');
});

document.getElementById('serviceForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const id = document.getElementById('editServiceId').value;
    const name = document.getElementById('serviceName').value;
    const description = document.getElementById('serviceDescription').value;
    const category = document.getElementById('serviceCategory').value;
    
    if (id) {
        const serviceIndex = services.findIndex(s => s.id == id);
        services[serviceIndex] = { id: parseInt(id), name, description, category };
    } else {
        const newId = services.length > 0 ? Math.max(...services.map(s => s.id)) + 1 : 1;
        services.push({ id: newId, name, description, category });
    }
    
    saveData();
    loadServices();
    closeModal('serviceModal');
});

document.getElementById('ticketForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const id = document.getElementById('editTicketId').value;
    const clientId = parseInt(document.getElementById('ticketClient').value);
    const serviceId = parseInt(document.getElementById('ticketService').value);
    const title = document.getElementById('ticketTitle').value;
    const description = document.getElementById('ticketDescription').value;
    const priority = document.getElementById('ticketPriority').value;
    const attendantId = document.getElementById('ticketAttendant').value;
    const status = document.getElementById('ticketStatus').value;
    const email = document.getElementById('ticketEmail').value;
    const newResponse = document.getElementById('newResponse').value.trim();
    
    if (id) {
        const ticketIndex = tickets.findIndex(t => t.id == id);
        
        // Atualizar dados principais do chamado
        tickets[ticketIndex] = { 
            ...tickets[ticketIndex],
            id: parseInt(id), 
            clientId, 
            serviceId, 
            title, 
            description, 
            priority, 
            attendantId: attendantId ? parseInt(attendantId) : null,
            status,
            email
        };
        
        // Adicionar nova resposta se houver
        if (newResponse) {
            if (!tickets[ticketIndex].responses) {
                tickets[ticketIndex].responses = [];
            }
            
            tickets[ticketIndex].responses.push({
                id: Date.now(),
                content: newResponse,
                userName: currentUser.name,
                userType: currentUser.type,
                date: new Date().toISOString()
            });
        }
    } else {
        const newId = tickets.length > 0 ? Math.max(...tickets.map(t => t.id)) + 1 : 1;
        const newTicket = { 
            id: newId, 
            clientId, 
            serviceId, 
            title, 
            description, 
            priority, 
            attendantId: attendantId ? parseInt(attendantId) : null,
            status,
            createdBy: currentUser.id,
            createdByName: currentUser.name,
            date: new Date().toISOString(),
            email,
            responses: []
        };
        
        // Adicionar resposta inicial se houver
        if (newResponse) {
            newTicket.responses.push({
                id: Date.now(),
                content: newResponse,
                userName: currentUser.name,
                userType: currentUser.type,
                date: new Date().toISOString()
            });
        }
        
        tickets.push(newTicket);
    }
    
    saveData();
    loadTickets();
    loadDashboard();
    closeModal('ticketModal');
});

function editUser(id) {
    if (currentUser.type !== 'admin') return;
    
    const user = users.find(u => u.id === id);
    document.getElementById('editUserId').value = user.id;
    document.getElementById('userName').value = user.name;
    document.getElementById('userUsername').value = user.username;
    document.getElementById('userPassword').value = user.password;
    document.getElementById('userType').value = user.type;
    
    // Popular lista de clientes
    const userClientSelect = document.getElementById('userClient');
    userClientSelect.innerHTML = '<option value="">Nenhum cliente</option>';
    clients.forEach(client => {
        userClientSelect.innerHTML += `<option value="${client.id}">${client.name}</option>`;
    });
    
    // Selecionar cliente vinculado
    if (user.clientId) {
        document.getElementById('userClient').value = user.clientId;
    }
    
    document.getElementById('userModal').style.display = 'block';
}

function editClient(id) {
    const client = clients.find(c => c.id === id);
    document.getElementById('editClientId').value = client.id;
    document.getElementById('clientName').value = client.name;
    document.getElementById('clientEmail').value = client.email;
    document.getElementById('clientPhone').value = client.phone || '';
    document.getElementById('clientCompany').value = client.company || '';
    document.getElementById('clientModal').style.display = 'block';
}

function editService(id) {
    const service = services.find(s => s.id === id);
    document.getElementById('editServiceId').value = service.id;
    document.getElementById('serviceName').value = service.name;
    document.getElementById('serviceDescription').value = service.description;
    document.getElementById('serviceCategory').value = service.category;
    document.getElementById('serviceModal').style.display = 'block';
}

function editTicket(id) {
    const ticket = tickets.find(t => t.id === id);
    
    // Para todos os usuários, usar o modal escuro
    showTicketModal(ticket);
    
    // Para users, desabilitar alguns campos
    if (currentUser.type === 'user') {
        // Limpar campo de nova resposta
        document.getElementById('newResponse').value = '';
        
        // Para users, desabilitar edição dos campos principais
        document.getElementById('ticketService').disabled = true;
        document.getElementById('ticketPriority').disabled = true;
        document.getElementById('ticketDescription').disabled = true;
        document.getElementById('ticketClient').disabled = true;
        document.getElementById('ticketStatus').disabled = true;
        
        // Focar no campo de nova resposta
        setTimeout(() => {
            const newResponseField = document.getElementById('newResponse');
            if (newResponseField) {
                newResponseField.focus();
            }
        }, 100);
    }
}

function showDetailedTicketModal(ticket) {
    const client = clients.find(c => c.id === ticket.clientId);
    const service = services.find(s => s.id === ticket.serviceId);
    const creator = users.find(u => u.id === ticket.createdBy);
    const attendant = ticket.attendantId ? users.find(u => u.id === ticket.attendantId) : null;
    const ticketDate = new Date(ticket.date);
    const formattedDateTime = `${ticketDate.toLocaleDateString('pt-BR')} ${ticketDate.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}`;
    
    // Gerar número de protocolo baseado no ID do chamado
    const protocolNumber = `#${ticket.id}`;
    
    // Popular os campos do modal
    document.getElementById('detailedTicketTitle').textContent = `Vincular Chamado: ${protocolNumber} - ${ticket.title || 'edes caravelas'}`;
    document.getElementById('detailedMessage').value = ticket.description || '';
    document.getElementById('detailedPriority').value = ticket.priority || 'alta';
    document.getElementById('detailedClient').value = 'hotel-caravelas';
    document.getElementById('detailedEmail').value = ticket.email || (client ? client.email : '') || '';
    document.getElementById('detailedStatus').value = ticket.status || 'aberto';
    
    // Popular dropdown de atendente
    const attendantSelect = document.getElementById('detailedAttendant');
    attendantSelect.innerHTML = '<option value="">Sem atendente</option>';
    const attendants = users.filter(user => user.type === 'admin' || user.type === 'tecnico');
    attendants.forEach(att => {
        const selected = ticket.attendantId === att.id ? 'selected' : '';
        attendantSelect.innerHTML += `<option value="${att.id}" ${selected}>${att.name}</option>`;
    });
    
    // Carregar histórico de respostas se existir
    loadDetailedTicketResponses(ticket);
    
    // Configurar botões de ação
    document.getElementById('deleteTicketBtn').onclick = () => deleteTicketDetailed(ticket.id);
    document.getElementById('saveChangesBtn').onclick = () => saveTicketChanges(ticket.id);
    
    document.getElementById('detailedTicketModal').style.display = 'block';
}

function loadDetailedTicketResponses(ticket) {
    const responsesContainer = document.getElementById('detailedResponses');
    responsesContainer.innerHTML = '';
    
    if (!ticket.responses || ticket.responses.length === 0) {
        responsesContainer.innerHTML = '<div class="empty-responses">Nenhuma resposta ainda. Seja o primeiro a responder!</div>';
        return;
    }
    
    ticket.responses.forEach(response => {
        const responseDiv = document.createElement('div');
        responseDiv.className = `response-item ${response.userType}-response`;
        responseDiv.innerHTML = `
            <div class="response-header">
                <span class="response-author">${response.userName} (${response.userType})</span>
                <span class="response-date">${new Date(response.date).toLocaleString('pt-BR')}</span>
            </div>
            <div class="response-content">${response.content}</div>
        `;
        responsesContainer.appendChild(responseDiv);
    });
    
    // Scroll para o final das respostas
    responsesContainer.scrollTop = responsesContainer.scrollHeight;
}

function saveTicketChanges(ticketId) {
    const ticket = tickets.find(t => t.id === ticketId);
    if (!ticket) return;
    
    // Atualizar campos básicos
    ticket.priority = document.getElementById('detailedPriority').value;
    ticket.status = document.getElementById('detailedStatus').value;
    ticket.attendantId = document.getElementById('detailedAttendant').value ? parseInt(document.getElementById('detailedAttendant').value) : null;
    
    // Adicionar nova resposta se houver
    const newResponse = document.getElementById('detailedNewResponse').value.trim();
    if (newResponse) {
        if (!ticket.responses) {
            ticket.responses = [];
        }
        
        ticket.responses.push({
            id: Date.now(),
            content: newResponse,
            userName: currentUser.name,
            userType: currentUser.type,
            date: new Date().toISOString()
        });
        
        document.getElementById('detailedNewResponse').value = '';
        loadDetailedTicketResponses(ticket);
    }
    
    saveData();
    loadTickets();
    loadDashboard();
    
    alert('Chamado atualizado com sucesso!');
}

function deleteTicketDetailed(ticketId) {
    if (confirm('Tem certeza que deseja excluir este chamado?')) {
        tickets = tickets.filter(t => t.id !== ticketId);
        saveData();
        loadTickets();
        loadDashboard();
        closeModal('detailedTicketModal');
    }
}

function loadTicketResponses(ticket) {
    const responsesContainer = document.getElementById('ticketResponses');
    responsesContainer.innerHTML = '';
    
    if (!ticket.responses || ticket.responses.length === 0) {
        responsesContainer.innerHTML = '<div class="empty-responses">Nenhuma resposta ainda. Seja o primeiro a responder!</div>';
        return;
    }
    
    ticket.responses.forEach(response => {
        const responseDiv = document.createElement('div');
        responseDiv.className = `response-item ${response.userType}-response`;
        responseDiv.innerHTML = `
            <div class="response-header">
                <span class="response-author">${response.userName} (${response.userType})</span>
                <span class="response-date">${new Date(response.date).toLocaleString()}</span>
            </div>
            <div class="response-content">${response.content}</div>
        `;
        responsesContainer.appendChild(responseDiv);
    });
    
    // Scroll para o final das respostas
    responsesContainer.scrollTop = responsesContainer.scrollHeight;
}

function deleteUser(id) {
    if (currentUser.type !== 'admin') return;
    
    if (confirm('Tem certeza que deseja excluir este usuário?')) {
        users = users.filter(u => u.id !== id);
        saveData();
        loadUsers();
    }
}

function deleteClient(id) {
    if (currentUser.type !== 'admin' && currentUser.type !== 'tecnico') {
        alert('Você não tem permissão para excluir clientes!');
        return;
    }
    
    if (confirm('Tem certeza que deseja excluir este cliente?')) {
        clients = clients.filter(c => c.id !== id);
        saveData();
        loadClients();
        loadDashboard();
    }
}

function deleteService(id) {
    if (currentUser.type !== 'admin') {
        alert('Você não tem permissão para excluir serviços!');
        return;
    }
    
    if (confirm('Tem certeza que deseja excluir este serviço?')) {
        services = services.filter(s => s.id !== id);
        saveData();
        loadServices();
        loadDashboard();
    }
}

function deleteTicket(id) {
    if (currentUser.type !== 'admin' && currentUser.type !== 'tecnico') {
        alert('Você não tem permissão para excluir chamados!');
        return;
    }
    
    if (confirm('Tem certeza que deseja excluir este chamado?')) {
        tickets = tickets.filter(t => t.id !== id);
        saveData();
        loadTickets();
        loadDashboard();
    }
}

// Funções de filtro para chamados
function filterUserTickets(filter) {
    // Atualizar botões ativos
    document.querySelectorAll('.tickets-filters .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Filtrar chamados do usuário
    let userTickets = tickets;
    if (currentUser.clientId) {
        userTickets = tickets.filter(t => t.clientId === currentUser.clientId);
    }
    
    if (filter === 'abertos') {
        userTickets = userTickets.filter(t => t.status !== 'fechado');
    } else if (filter === 'fechados') {
        userTickets = userTickets.filter(t => t.status === 'fechado');
    }
    
    const ticketsList = document.getElementById('userTicketsList');
    loadTicketsList(ticketsList, userTickets, 'Nenhum chamado encontrado.');
}

function filterTicketsTable(filter) {
    // Atualizar botões ativos
    document.querySelectorAll('.tickets-filters .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Filtrar chamados na tabela
    let filteredTickets = tickets;
    
    if (filter === 'abertos') {
        filteredTickets = tickets.filter(t => t.status !== 'fechado');
    } else if (filter === 'fechados') {
        filteredTickets = tickets.filter(t => t.status === 'fechado');
    }
    
    // Recarregar tabela com filtro
    const tbody = document.querySelector('#ticketsTable tbody');
    tbody.innerHTML = '';
    
    const canEditTickets = currentUser.type === 'admin' || currentUser.type === 'tecnico';
    const canDeleteTickets = currentUser.type === 'admin';
    
    filteredTickets.forEach(ticket => {
        const client = clients.find(c => c.id === ticket.clientId);
        const service = services.find(s => s.id === ticket.serviceId);
        const attendant = ticket.attendantId ? users.find(u => u.id === ticket.attendantId) : null;
        const ticketDate = new Date(ticket.date);
        const formattedDateTime = `${ticketDate.toLocaleDateString()} ${ticketDate.toLocaleTimeString()}`;
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ticket.id}</td>
            <td>${ticket.createdByName || 'N/A'}</td>
            <td>${ticket.title}</td>
            <td>${client ? client.name : 'N/A'}</td>
            <td>${service ? service.name : 'N/A'}</td>
            <td>${formattedDateTime}</td>
            <td>${attendant ? `${attendant.name}` : 'Não atribuído'}</td>
            <td>
                <button onclick="editTicket(${ticket.id})" ${!canEditTickets ? 'disabled' : ''}>Editar</button>
                <button onclick="deleteTicket(${ticket.id})" ${!canDeleteTickets ? 'disabled' : ''}>Excluir</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Funções para o modal detalhado
function updateAttendant(ticketId, attendantId) {
    const ticketIndex = tickets.findIndex(t => t.id == ticketId);
    if (ticketIndex !== -1) {
        tickets[ticketIndex].attendantId = attendantId ? parseInt(attendantId) : null;
        saveData();
        
        // Atualizar visualização
        loadTickets();
        loadDashboard();
    }
}

function showConversationModal(ticketId) {
    // Implementar modal de conversação
    alert('Modal de conversação será implementado');
}

function editTicketDetailed(ticketId) {
    const ticket = tickets.find(t => t.id == ticketId);
    
    // Fechar modal detalhado e abrir modal de edição padrão
    closeModal('detailedTicketModal');
    
    document.getElementById('editTicketId').value = ticket.id;
    document.getElementById('ticketClient').value = ticket.clientId;
    document.getElementById('ticketService').value = ticket.serviceId;
    document.getElementById('ticketTitle').value = ticket.title;
    document.getElementById('ticketDescription').value = ticket.description;
    document.getElementById('ticketPriority').value = ticket.priority;
    document.getElementById('ticketAttendant').value = ticket.attendantId || '';
    document.getElementById('ticketStatus').value = ticket.status;
    
    showTicketModal();
    
    // Restaurar título original para admin/técnico
    document.querySelector('#ticketModal h2').textContent = 'Editar Chamado';
    
    // Reabilitar campos para admin/técnico
    document.getElementById('ticketTitle').disabled = false;
    document.getElementById('ticketService').disabled = false;
    document.getElementById('ticketPriority').disabled = false;
    document.getElementById('ticketDescription').disabled = false;
}

function deleteTicketDetailed(ticketId) {
    if (confirm('Tem certeza que deseja excluir este chamado?')) {
        tickets = tickets.filter(t => t.id != ticketId);
        saveData();
        loadTickets();
        loadDashboard();
        closeModal('detailedTicketModal');
    }
}

window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}


function deleteTicketFromModal() {
    if (currentUser.type !== 'admin' && currentUser.type !== 'tecnico') {
        alert('Você não tem permissão para excluir chamados!');
        return;
    }
    
    const ticketId = parseInt(document.getElementById('editTicketId').value);
    if (!ticketId) return;
    
    if (confirm('Tem certeza que deseja excluir este chamado?')) {
        tickets = tickets.filter(t => t.id !== ticketId);
        saveData();
        loadTickets();
        loadDashboard();
        closeModal('ticketModal');
        alert('Chamado excluído com sucesso!');
    }
    
    document.getElementById('ticketMaisDropdown').classList.remove('show');
}

function printTicket() {
    const ticketId = parseInt(document.getElementById('editTicketId').value);
    if (!ticketId) return;
    
    const ticket = tickets.find(t => t.id === ticketId);
    if (!ticket) return;
    
    // Criar janela de impressão
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
            <head>
                <title>Chamado #${ticket.id}</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    h1 { color: #333; }
                    .info { margin: 10px 0; }
                    .responses { margin-top: 20px; }
                    .response { border: 1px solid #ccc; padding: 10px; margin: 10px 0; }
                </style>
            </head>
            <body>
                <h1>Detalhes do Chamado #${ticket.id}</h1>
                <div class="info"><strong>Assunto:</strong> ${ticket.title || ''}</div>
                <div class="info"><strong>Descrição:</strong> ${ticket.description || ''}</div>
                <div class="info"><strong>Prioridade:</strong> ${ticket.priority || ''}</div>
                <div class="info"><strong>Status:</strong> ${ticket.status || ''}</div>
                <div class="info"><strong>Data:</strong> ${new Date(ticket.date).toLocaleString('pt-BR')}</div>
                ${ticket.responses && ticket.responses.length > 0 ? `
                    <div class="responses">
                        <h3>Histórico de Conversação:</h3>
                        ${ticket.responses.map(r => `
                            <div class="response">
                                <strong>${r.userName} (${r.userType}):</strong><br>
                                ${r.content}<br>
                                <small>${new Date(r.date).toLocaleString('pt-BR')}</small>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
    
    document.getElementById('ticketMaisDropdown').classList.remove('show');
}

// Função para controlar o dropdown do botão "Mais"
function toggleTicketMaisDropdown() {
    const dropdown = document.getElementById('ticketMaisDropdown');
    dropdown.classList.toggle('show');
}

// Função para ativar/desativar modo de edição
function toggleEditMode() {
    const isEditMode = document.body.classList.contains('ticket-edit-mode');
    
    if (isEditMode) {
        // Sair do modo de edição
        exitEditMode();
    } else {
        // Entrar no modo de edição
        enterEditMode();
    }
    
    // Fechar dropdown
    document.getElementById('ticketMaisDropdown').classList.remove('show');
}

function enterEditMode() {
    // Verificar permissões
    if (currentUser.type !== 'admin' && currentUser.type !== 'tecnico') {
        alert('Você não tem permissão para editar chamados!');
        return;
    }
    
    document.body.classList.add('ticket-edit-mode');
    setTicketFieldsReadonly(false);
    
    // Adicionar indicador de modo de edição
    const titleElement = document.getElementById('ticketTitle');
    if (!titleElement.querySelector('.ticket-edit-indicator')) {
        const indicator = document.createElement('span');
        indicator.className = 'ticket-edit-indicator';
        indicator.textContent = 'EDITANDO';
        titleElement.appendChild(indicator);
    }
    
    // Alterar botão "Mais" para "Salvar"
    const maisBtn = document.getElementById('ticketMaisBtn');
    maisBtn.textContent = 'Salvar ✓';
    maisBtn.className = 'btn-save-edit';
}

function exitEditMode() {
    // Salvar alterações
    saveTicketChanges();
    
    document.body.classList.remove('ticket-edit-mode');
    setTicketFieldsReadonly(true);
    
    // Remover indicador de modo de edição
    const indicator = document.querySelector('.ticket-edit-indicator');
    if (indicator) {
        indicator.remove();
    }
    
    // Restaurar botão "Mais"
    const maisBtn = document.getElementById('ticketMaisBtn');
    maisBtn.textContent = 'Mais ▼';
    maisBtn.className = 'btn-mais-chamado';
}

function setTicketFieldsReadonly(readonly) {
    const fields = [
        'ticketDescription',
        'ticketPriority',
        'ticketClient',
        'ticketService',
        'ticketSubject',
        'ticketStatus',
        'ticketAttendant',
        'ticketEmail'
    ];
    
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            // Usuários comuns nunca podem editar campos (apenas adicionar respostas)
            const forceReadonly = currentUser.type === 'user' && document.getElementById('editTicketId').value;
            
            if (field.tagName === 'SELECT') {
                field.disabled = readonly || forceReadonly;
            } else {
                field.readOnly = readonly || forceReadonly;
            }
        }
    });
    
    // Não há campos que sempre ficam readonly
}

function saveTicketChanges() {
    const ticketId = parseInt(document.getElementById('editTicketId').value);
    if (!ticketId) return;
    
    const ticketIndex = tickets.findIndex(t => t.id === ticketId);
    if (ticketIndex === -1) return;
    
    // Atualizar dados do ticket (apenas admin e técnico podem modificar)
    if (currentUser.type === 'admin' || currentUser.type === 'tecnico') {
        tickets[ticketIndex].description = document.getElementById('ticketDescription').value;
        tickets[ticketIndex].priority = document.getElementById('ticketPriority').value;
        tickets[ticketIndex].clientId = parseInt(document.getElementById('ticketClient').value);
        tickets[ticketIndex].serviceId = parseInt(document.getElementById('ticketService').value);
        tickets[ticketIndex].attendantId = document.getElementById('ticketAttendant').value ? parseInt(document.getElementById('ticketAttendant').value) : null;
        tickets[ticketIndex].status = document.getElementById('ticketStatus').value;
        tickets[ticketIndex].email = document.getElementById('ticketEmail').value;
    }
    
    // Adicionar resposta se houver
    const newResponse = document.getElementById('newResponse');
    if (newResponse && newResponse.value.trim()) {
        if (!tickets[ticketIndex].responses) {
            tickets[ticketIndex].responses = [];
        }
        
        tickets[ticketIndex].responses.push({
            id: Date.now(),
            content: newResponse.value.trim(),
            userName: currentUser.name,
            userType: currentUser.type,
            date: new Date().toISOString()
        });
        
        newResponse.value = '';
        loadTicketResponses(tickets[ticketIndex]);
    }
    
    saveData();
    loadTickets();
    loadDashboard();
    
    // Mensagem diferente para cada tipo de usuário
    if (currentUser.type === 'user') {
        alert('Resposta adicionada com sucesso!');
    } else {
        alert('Chamado atualizado com sucesso!');
    }
}

function viewTicketHistory() {
    const ticketId = parseInt(document.getElementById('editTicketId').value);
    if (!ticketId) return;
    
    const ticket = tickets.find(t => t.id === ticketId);
    if (!ticket) return;
    
    // Mostrar seção de respostas
    document.getElementById('ticketResponsesSection').style.display = 'block';
    loadTicketResponses(ticket);
    
    // Fechar dropdown
    document.getElementById('ticketMaisDropdown').classList.remove('show');
}

function reassignTicket() {
    if (currentUser.type !== 'admin') {
        alert('Você não tem permissão para reatribuir chamados!');
        return;
    }
    
    const ticketId = parseInt(document.getElementById('editTicketId').value);
    if (!ticketId) return;
    
    const technicians = users.filter(user => user.type === 'admin' || user.type === 'tecnico');
    let options = '<option value="">Selecione um técnico</option>';
    technicians.forEach(tech => {
        options += `<option value="${tech.id}">${tech.name} (${tech.type})</option>`;
    });
    
    const newAttendant = prompt(`Reatribuir chamado para:\n\n${options}`, '');
    if (newAttendant) {
        const ticket = tickets.find(t => t.id === ticketId);
        if (ticket) {
            ticket.attendantId = parseInt(newAttendant) || null;
            saveData();
            loadTickets();
            loadDashboard();
            
            // Atualizar interface
            document.getElementById('ticketAttendant').value = ticket.attendantId || '';
            alert('Chamado reatribuído com sucesso!');
        }
    }
    
    document.getElementById('ticketMaisDropdown').classList.remove('show');
}

function changeTicketPriority() {
    if (currentUser.type !== 'admin') {
        alert('Você não tem permissão para alterar prioridade de chamados!');
        return;
    }
    
    const ticketId = parseInt(document.getElementById('editTicketId').value);
    if (!ticketId) return;
    
    const priorities = ['baixa', 'media', 'alta', 'critica'];
    const priorityLabels = ['Baixa', 'Média', 'Alta', 'Crítica'];
    
    let options = '';
    priorities.forEach((priority, index) => {
        options += `${index + 1}. ${priorityLabels[index]}\n`;
    });
    
    const selection = prompt(`Alterar prioridade do chamado:\n\n${options}\nDigite o número da prioridade:`, '');
    if (selection && selection >= 1 && selection <= 4) {
        const newPriority = priorities[selection - 1];
        const ticket = tickets.find(t => t.id === ticketId);
        if (ticket) {
            ticket.priority = newPriority;
            saveData();
            loadTickets();
            loadDashboard();
            
            // Atualizar interface
            document.getElementById('ticketPriority').value = newPriority;
            alert(`Prioridade alterada para: ${priorityLabels[selection - 1]}`);
        }
    }
    
    document.getElementById('ticketMaisDropdown').classList.remove('show');
}

function transferTicket() {
    // Função para administradores transferirem tickets
    alert('Funcionalidade de transferência em desenvolvimento');
    document.getElementById('ticketMaisDropdown').classList.remove('show');
}

// Fechar dropdown quando clicar fora
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('ticketMaisDropdown');
    const container = document.getElementById('ticketMaisContainer');
    
    if (dropdown && container && !container.contains(event.target)) {
        dropdown.classList.remove('show');
    }
});

initializeData();