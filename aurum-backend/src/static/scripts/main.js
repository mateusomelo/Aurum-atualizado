// Main JavaScript for Aurum Website

// Hero Carousel Variables (Global Scope)
let currentHeroSlideIndex = 0;
let heroAutoPlayInterval;
let heroSlides;
let heroIndicators;
let heroThumbnails;
let totalHeroSlides;

// Hero Carousel Functions (Global Scope)
function changeHeroSlide(direction) {
    currentHeroSlideIndex += direction;

    if (currentHeroSlideIndex >= totalHeroSlides) {
        currentHeroSlideIndex = 0;
    } else if (currentHeroSlideIndex < 0) {
        currentHeroSlideIndex = totalHeroSlides - 1;
    }

    updateHeroCarousel();
}

function goToHeroSlide(index) {
    currentHeroSlideIndex = index;
    updateHeroCarousel();
}

function updateHeroCarousel() {
    // Atualizar slides
    heroSlides.forEach((slide, index) => {
        slide.classList.remove("active");
        if (index === currentHeroSlideIndex) {
            slide.classList.add("active");
        }
    });

    // Atualizar indicadores
    heroIndicators.forEach((indicator, index) => {
        indicator.classList.remove("active");
        if (index === currentHeroSlideIndex) {
            indicator.classList.add("active");
        }
    });

    // Atualizar miniaturas
    heroThumbnails.forEach((thumbnail, index) => {
        thumbnail.classList.remove("active");
        if (index === currentHeroSlideIndex) {
            thumbnail.classList.add("active");
        }
    });

    // Adicionar animação aos elementos do slide ativo
    const activeSlide = heroSlides[currentHeroSlideIndex];
    if (activeSlide) {
        const heroContent = activeSlide.querySelector(".hero-content");
        const heroImage = activeSlide.querySelector(".hero-image");

        if (heroContent) {
            heroContent.style.animation = "none";
            heroContent.offsetHeight; // Trigger reflow
            heroContent.style.animation = "slideInLeft 0.8s ease-out";
        }

        if (heroImage) {
            heroImage.style.animation = "none";
            heroImage.offsetHeight; // Trigger reflow
            heroImage.style.animation = "slideInRight 0.8s ease-out";
        }
    }

    // Atualizar título da página baseado no slide atual
    updatePageTitle();
}

function updatePageTitle() {
    const activeSlide = heroSlides[currentHeroSlideIndex];
    if (activeSlide) {
        const title = activeSlide.querySelector(".hero-title").textContent;
        document.title = `${title} | Aurum - Soluções Integradas em T.I.`;
    }
}

function startHeroAutoPlay() {
    stopHeroAutoPlay(); // Limpar qualquer interval existente
    heroAutoPlayInterval = setInterval(() => {
        changeHeroSlide(1);
    }, 3000); // Troca a cada 1.5 segundos
}

function stopHeroAutoPlay() {
    if (heroAutoPlayInterval) {
        clearInterval(heroAutoPlayInterval);
        heroAutoPlayInterval = null;
    }
}

document.addEventListener("DOMContentLoaded", function() {
    // Initialize Hero Carousel Variables
    heroSlides = document.querySelectorAll(".hero-slide");
    heroIndicators = document.querySelectorAll(".hero-indicator");
    heroThumbnails = document.querySelectorAll(".hero-thumbnail");
    totalHeroSlides = heroSlides.length;

    // Mobile menu toggle
    const hamburger = document.querySelector(".hamburger");
    const navMenu = document.querySelector(".nav-menu");
    
    if (hamburger && navMenu) {
        hamburger.addEventListener("click", function() {
            hamburger.classList.toggle("active");
            navMenu.classList.toggle("active");
        });
        
        // Close menu when clicking on a link
        document.querySelectorAll(".nav-link").forEach(link => {
            link.addEventListener("click", () => {
                hamburger.classList.remove("active");
                navMenu.classList.remove("active");
            });
        });
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll("a[href^=\"#\"]").forEach(anchor => {
        anchor.addEventListener("click", function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute("href"));
            if (target) {
                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            }
        });
    });
    
    // EmailJS Configuration - CONFIGURE ESTES VALORES APÓS CRIAR SUA CONTA
    const EMAILJS_CONFIG = {
        serviceID: 'service_tonz2t8',      // Ex: 'service_abc123'
        templateID: 'template_nfbgifo',    // Ex: 'template_def456'
        publicKey: 'czv_mghrVuYGt97EH'       // Ex: 'ghi789jkl012'
    };

    // Initialize EmailJS
    emailjs.init(EMAILJS_CONFIG.publicKey);

    // Contact form handling com EmailJS
    const contactForm = document.getElementById("contactForm");
    if (contactForm) {
        contactForm.addEventListener("submit", function(e) {
            e.preventDefault();
            
            // Show loading state
            const submitBtn = this.querySelector("button[type=\"submit\"]");
            const originalText = submitBtn.textContent;
            submitBtn.textContent = "Enviando...";
            submitBtn.disabled = true;
            
            // Get form data
            const now = new Date();
            const formData = {
                from_name: document.getElementById('name').value,
                from_email: document.getElementById('email').value,
                subject: document.getElementById('subject').value,
                message: document.getElementById('message').value,
                to_email: 'contato@aurum.inf.br',
                current_date: now.toLocaleDateString('pt-BR') + ' às ' + now.toLocaleTimeString('pt-BR')
            };
            
            // Send email via EmailJS
            emailjs.send(EMAILJS_CONFIG.serviceID, EMAILJS_CONFIG.templateID, formData)
                .then(function(response) {
                    showMessage("✅ Mensagem enviada com sucesso! Entraremos em contato em breve.", "success");
                    contactForm.reset();
                }, function(error) {
                    console.error('EmailJS Error:', error);
                    showMessage("❌ Erro ao enviar mensagem. Tente novamente.", "error");
                })
                .finally(() => {
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                });
        });
    }
    
    // Intersection Observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("fade-in");
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    document.querySelectorAll(".service-card, .about-content, .clients-content").forEach(el => {
        observer.observe(el);
    });
    
    // Header scroll effect
    const header = document.querySelector(".header");
    if (header) {
        window.addEventListener("scroll", function() {
            if (window.scrollY > 100) {
                header.style.background = "rgba(255, 255, 255, 0.95)";
                header.style.backdropFilter = "blur(10px)";
            } else {
                header.style.background = "#fff";
                header.style.backdropFilter = "none";
            }
        });
    }

    function initHeroCarousel() {
        console.log("initHeroCarousel called. heroSlides.length:", heroSlides.length);
        if (heroSlides.length > 0) {
            // Configurar slide inicial
            updateHeroCarousel();

            // Iniciar auto-play
            startHeroAutoPlay();

            // Adicionar event listeners para pausar/retomar auto-play
            const heroContainer = document.querySelector(".hero");
            if (heroContainer) {
                heroContainer.addEventListener("mouseenter", stopHeroAutoPlay);
                heroContainer.addEventListener("mouseleave", startHeroAutoPlay);
            }

            // Adicionar suporte para navegação por teclado
            document.addEventListener("keydown", function(e) {
                // Só funcionar se estivermos na seção hero
                const heroSection = document.querySelector(".hero");
                if (heroSection) {
                    const rect = heroSection.getBoundingClientRect();
                    const isHeroVisible = rect.top < window.innerHeight && rect.bottom > 0;

                    if (isHeroVisible) {
                        if (e.key === "ArrowLeft") {
                            e.preventDefault();
                            changeHeroSlide(-1);
                        } else if (e.key === "ArrowRight") {
                            e.preventDefault();
                            changeHeroSlide(1);
                        }
                    }
                }
            });

            // Adicionar suporte para touch/swipe em dispositivos móveis
            let startX = 0;
            let endX = 0;

            if (heroContainer) {
                heroContainer.addEventListener("touchstart", function(e) {
                    startX = e.touches[0].clientX;
                });

                heroContainer.addEventListener("touchend", function(e) {
                    endX = e.changedTouches[0].clientX;
                    handleHeroSwipe();
                });
            }

            function handleHeroSwipe() {
                const threshold = 50; // Mínimo de pixels para considerar um swipe
                const diff = startX - endX;

                if (Math.abs(diff) > threshold) {
                    if (diff > 0) {
                        changeHeroSlide(1); // Swipe para a esquerda - próximo slide
                    } else {
                        changeHeroSlide(-1); // Swipe para a direita - slide anterior
                    }
                }
            }
        }
    }

    // Initialize Hero Carousel
    initHeroCarousel();

    // Pausar auto-play quando a aba não estiver visível
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            stopHeroAutoPlay();
        } else {
            startHeroAutoPlay();
        }
    });

    // Pausar auto-play quando o usuário rolar para fora da seção hero
    function handleHeroScroll() {
        const heroSection = document.querySelector(".hero");
        if (heroSection) {
            const rect = heroSection.getBoundingClientRect();
            const isHeroVisible = rect.top < window.innerHeight && rect.bottom > 0;

            if (isHeroVisible) {
                startHeroAutoPlay();
            } else {
                stopHeroAutoPlay();
            }
        }
    }

    window.addEventListener("scroll", handleHeroScroll);

    // Utility functions
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    function showMessage(message, type = "info") {
        // Remove existing messages
        const existingMessages = document.querySelectorAll(".message-toast");
        existingMessages.forEach(msg => msg.remove());
        
        // Create message element
        const messageEl = document.createElement("div");
        messageEl.className = `message-toast message-${type}`;
        messageEl.textContent = message;
        
        // Style the message
        Object.assign(messageEl.style, {
            position: "fixed",
            top: "20px",
            right: "20px",
            padding: "1rem 1.5rem",
            borderRadius: "0.5rem",
            color: "white",
            fontWeight: "500",
            zIndex: "9999",
            maxWidth: "400px",
            boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
            animation: "slideInFromRight 0.3s ease-out"
        });
        
        // Set background color based on type
        switch (type) {
            case "success":
                messageEl.style.background = "#10b981";
                break;
            case "error":
                messageEl.style.background = "#ef4444";
                break;
            case "warning":
                messageEl.style.background = "#f59e0b";
                break;
            default:
                messageEl.style.background = "#2563eb";
        }
        
        // Add to page
        document.body.appendChild(messageEl);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            messageEl.style.animation = "slideOutToRight 0.3s ease-in";
            setTimeout(() => {
                if (messageEl.parentNode) {
                    messageEl.remove();
                }
            }, 300);
        }, 5000);
    }

    // Add CSS animations for messages
    const style = document.createElement("style");
    style.textContent = `
        @keyframes slideInFromRight {
            from {
                opacity: 0;
                transform: translateX(100px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideOutToRight {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(100px);
            }
        }
    `;
    document.head.appendChild(style);

    // Client Carousel
    function resizeImage(imgElement, maxWidth, maxHeight) {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        let width = imgElement.width;
        let height = imgElement.height;

        // Calculate new dimensions, maintaining aspect ratio
        if (maxWidth && width > maxWidth) {
            height = height * (maxWidth / width);
            width = maxWidth;
        }

        if (maxHeight && height > maxHeight) {
            width = width * (maxHeight / height);
            height = maxHeight;
        }

        canvas.width = width;
        canvas.height = height;

        ctx.drawImage(imgElement, 0, 0, width, height);

        // Return the resized image as a data URL (e.g., PNG)
        return canvas.toDataURL("image/png");
    }

    // Client Carousel
    const clients = [
        {
            name: "BEST GUEST HOTEL",
            image: "/assets/bestguest.png"
        },
        {
            name: "FSMAX SYSTEMS",
            image: "/assets/fsmax.jpeg"
        },
        {
            name: "MOREIRA FILHO ADVOGADOS",
            image: "/assets/moreirafilho.jpeg"
        },
        {
            name: "ED.HYDE PARK",
            image: "/assets/edhyde.png"
        },
        {
            name: "SP CENTRO",
            image: "/assets/spcentro.png"
        },
        {
            name: "NOVAES & ROSELLI ADVOGADOS",
            image: "/assets/novaesroselli.jpeg" 
        },
    ];

    let currentIndex = 0;
    const clientNameElement = document.getElementById("client-name");
    const clientMessageElement = document.getElementById("client-message");
    const clientImageElement = document.getElementById("client-image");
    const clientsTextElement = document.querySelector(".clients-text");

    function updateClientInfo() {
        // Add fade out effect
        if (clientsTextElement) clientsTextElement.style.opacity = "0";
        if (clientImageElement) clientImageElement.style.opacity = "0";
        
        setTimeout(() => {
            const currentClient = clients[currentIndex];
            if (clientNameElement) clientNameElement.textContent = currentClient.name;
            if (clientMessageElement) clientMessageElement.textContent = currentClient.message || "";
            
            // Create a temporary image element to load the image and then resize it
            const tempImage = new Image();
            tempImage.src = currentClient.image;

            tempImage.onload = () => {
                if (clientImageElement) {
                    // Define as dimensões desejadas para a sua logo (ex: 150px de largura, altura automática)
                    const resizedDataURL = resizeImage(tempImage, 200, null); 
                    clientImageElement.src = resizedDataURL;
                    clientImageElement.style.width = "300px";
                    clientImageElement.style.height = "200px";

                    // Add fade in effect after image is loaded and resized
                    if (clientsTextElement) {
                        clientsTextElement.style.opacity = "1";
                        clientsTextElement.classList.add("client-fade-in");
                    }
                    clientImageElement.style.opacity = "1";
                    clientImageElement.classList.add("client-fade-in");
                }
            };
        }, 300);
    }

    function nextClient() {
        currentIndex = (currentIndex + 1) % clients.length;
        updateClientInfo();
    }

    function prevClient() {
        currentIndex = (currentIndex - 1 + clients.length) % clients.length;
        updateClientInfo();
    }

    // Initialize client carousel
    if (clientNameElement) {
        updateClientInfo();
        
        // Auto-advance every 4 seconds
        setInterval(nextClient, 3000);
        
        // Add click handlers for navigation (if you have prev/next buttons)
        const prevClientBtn = document.getElementById("prevClient");
        const nextClientBtn = document.getElementById("nextClient");
        
        if (prevClientBtn) prevClientBtn.addEventListener("click", prevClient);
        if (nextClientBtn) nextClientBtn.addEventListener("click", nextClient);
    }
});

