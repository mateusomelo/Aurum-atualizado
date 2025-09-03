// Dashboard JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.classList.contains('alert-success')) {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Phone number formatting
    var phoneInputs = document.querySelectorAll('input[name="telefone"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            var value = input.value.replace(/\D/g, '');
            if (value.length <= 11) {
                value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
                if (value.length < 14) {
                    value = value.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
                }
            }
            input.value = value;
        });
    });

    // CNPJ formatting
    var cnpjInputs = document.querySelectorAll('input[name="cnpj"]');
    cnpjInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            var value = input.value.replace(/\D/g, '');
            value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            input.value = value;
        });
    });

    // Confirm delete actions
    var deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Tem certeza que deseja excluir este item?')) {
                window.location.href = button.href;
            }
        });
    });

    // Auto-refresh dashboard (every 30 seconds)
    if (document.querySelector('.dashboard')) {
        setInterval(function() {
            // Only refresh if user is still active (moved mouse in last 5 minutes)
            var lastActivity = parseInt(localStorage.getItem('lastActivity') || '0');
            var now = Date.now();
            if (now - lastActivity < 5 * 60 * 1000) { // 5 minutes
                location.reload();
            }
        }, 30000);

        // Track user activity
        document.addEventListener('mousemove', function() {
            localStorage.setItem('lastActivity', Date.now().toString());
        });
    }

    // Search functionality
    var searchInput = document.querySelector('#searchTickets');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            var searchTerm = this.value.toLowerCase();
            var tickets = document.querySelectorAll('.ticket-card');
            
            tickets.forEach(function(ticket) {
                var title = ticket.querySelector('.card-title').textContent.toLowerCase();
                var description = ticket.querySelector('.card-text').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || description.includes(searchTerm)) {
                    ticket.parentElement.style.display = '';
                } else {
                    ticket.parentElement.style.display = 'none';
                }
            });
        });
    }

    // Status filter
    var statusFilter = document.querySelector('#statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            var selectedStatus = this.value;
            var tickets = document.querySelectorAll('.ticket-card');
            
            tickets.forEach(function(ticket) {
                var status = ticket.dataset.status;
                
                if (selectedStatus === '' || status === selectedStatus) {
                    ticket.parentElement.style.display = '';
                } else {
                    ticket.parentElement.style.display = 'none';
                }
            });
        });
    }

    // Priority filter
    var priorityFilter = document.querySelector('#priorityFilter');
    if (priorityFilter) {
        priorityFilter.addEventListener('change', function() {
            var selectedPriority = this.value;
            var tickets = document.querySelectorAll('.ticket-card');
            
            tickets.forEach(function(ticket) {
                var priority = ticket.dataset.priority;
                
                if (selectedPriority === '' || priority === selectedPriority) {
                    ticket.parentElement.style.display = '';
                } else {
                    ticket.parentElement.style.display = 'none';
                }
            });
        });
    }

    // Loading states for forms
    var forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            var submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processando...';
            }
        });
    });

    // Character counter for textareas
    var textareas = document.querySelectorAll('textarea');
    textareas.forEach(function(textarea) {
        var maxLength = textarea.getAttribute('maxlength');
        if (maxLength) {
            var counter = document.createElement('small');
            counter.className = 'form-text text-muted text-end d-block';
            counter.id = textarea.id + '_counter';
            textarea.parentNode.appendChild(counter);
            
            function updateCounter() {
                var remaining = maxLength - textarea.value.length;
                counter.textContent = remaining + ' caracteres restantes';
                if (remaining < 50) {
                    counter.className = 'form-text text-warning text-end d-block';
                } else {
                    counter.className = 'form-text text-muted text-end d-block';
                }
            }
            
            textarea.addEventListener('input', updateCounter);
            updateCounter();
        }
    });
});

// Utility functions
function formatDate(dateString) {
    var date = new Date(dateString);
    return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR');
}

function getStatusBadgeClass(status) {
    switch(status) {
        case 'aberto': return 'bg-danger';
        case 'em_andamento': return 'bg-warning';
        case 'finalizado': return 'bg-success';
        default: return 'bg-secondary';
    }
}

function getPriorityBadgeClass(priority) {
    switch(priority) {
        case 'baixa': return 'bg-info';
        case 'media': return 'bg-warning';
        case 'alta': return 'bg-danger';
        default: return 'bg-secondary';
    }
}
