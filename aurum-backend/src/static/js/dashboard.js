// Dashboard JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Admin sidebar functionality for mobile
    const adminSidebar = document.getElementById('adminSidebar');
    const adminSidebarToggle = document.getElementById('adminSidebarToggle');
    const adminSidebarOverlay = document.getElementById('adminSidebarOverlay');
    
    if (adminSidebar && adminSidebarToggle && adminSidebarOverlay) {
        // Toggle sidebar
        adminSidebarToggle.addEventListener('click', function() {
            adminSidebar.classList.toggle('show');
            adminSidebarOverlay.classList.toggle('show');
        });
        
        // Close sidebar when clicking overlay
        adminSidebarOverlay.addEventListener('click', function() {
            adminSidebar.classList.remove('show');
            adminSidebarOverlay.classList.remove('show');
        });
        
        // Close sidebar on window resize if desktop size
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                adminSidebar.classList.remove('show');
                adminSidebarOverlay.classList.remove('show');
            }
        });
    }
    
    // Highlight active navigation item and expand parent menu
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.admin-sidebar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
            
            // If this is a submenu item, expand the parent menu
            const parentCollapse = link.closest('.collapse');
            if (parentCollapse) {
                parentCollapse.classList.add('show');
                const trigger = document.querySelector(`[data-bs-target="#${parentCollapse.id}"]`);
                if (trigger) {
                    trigger.setAttribute('aria-expanded', 'true');
                }
            }
        }
    });
    
    // Handle sidebar dropdown toggles
    const dropdownToggles = document.querySelectorAll('.admin-sidebar-nav .dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            // Check if the click is on the arrow or if it's meant to expand/collapse
            const rect = this.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const arrowArea = rect.width - 30; // Arrow is usually in the last 30px
            
            // If clicking on the arrow area (right side) or the link has no href, handle dropdown
            if (clickX > arrowArea || this.getAttribute('href') === '#') {
                e.preventDefault();
                const targetId = this.getAttribute('data-bs-target');
                const target = document.querySelector(targetId);
                
                if (target) {
                    // Close other open menus
                    const allCollapses = document.querySelectorAll('.admin-sidebar-nav .collapse');
                    allCollapses.forEach(collapse => {
                        if (collapse !== target && collapse.classList.contains('show')) {
                            collapse.classList.remove('show');
                            const otherTrigger = document.querySelector(`[data-bs-target="#${collapse.id}"]`);
                            if (otherTrigger) {
                                otherTrigger.setAttribute('aria-expanded', 'false');
                            }
                        }
                    });
                    
                    // Toggle current menu
                    const isExpanded = this.getAttribute('aria-expanded') === 'true';
                    target.classList.toggle('show');
                    this.setAttribute('aria-expanded', !isExpanded);
                }
            }
            // Otherwise, let the link navigate normally
        });
    });
    
    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.classList.contains('show')) {
                alert.classList.remove('show');
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }
        }, 5000);
    });
});