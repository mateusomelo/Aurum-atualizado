// Services Carousel Implementation
class ServicesCarousel {
    constructor() {
        this.carousel = document.getElementById('servicesCarousel');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.indicatorsContainer = document.getElementById('carouselIndicators');
        
        this.currentIndex = 0;
        this.totalCards = 0;
        this.cardsPerView = 3; // Default for desktop
        this.autoSlideInterval = null;
        this.autoSlideDelay = 4000; // 5 seconds
        
        this.init();
    }
    
    init() {
        if (!this.carousel) return;
        
        this.totalCards = this.carousel.children.length;
        this.updateCardsPerView();
        this.createIndicators();
        this.bindEvents();
        this.startAutoSlide();
        
        // Update on window resize
        window.addEventListener('resize', () => {
            this.updateCardsPerView();
            this.updateCarousel();
            this.updateIndicators();
        });
    }
    
    updateCardsPerView() {
        const width = window.innerWidth;
        
        if (width <= 768) {
            this.cardsPerView = 1; // Mobile
        } else if (width <= 1024) {
            this.cardsPerView = 2; // Tablet
        } else {
            this.cardsPerView = 3; // Desktop
        }
    }
    
    createIndicators() {
        if (!this.indicatorsContainer) return;
        
        this.indicatorsContainer.innerHTML = '';
        const totalSlides = Math.ceil(this.totalCards / this.cardsPerView);
        
        for (let i = 0; i < totalSlides; i++) {
            const indicator = document.createElement('div');
            indicator.className = 'carousel-indicator';
            indicator.setAttribute('data-slide', i);
            
            if (i === 0) {
                indicator.classList.add('active');
            }
            
            indicator.addEventListener('click', () => {
                this.goToSlide(i);
            });
            
            this.indicatorsContainer.appendChild(indicator);
        }
    }
    
    bindEvents() {
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => {
                this.prevSlide();
            });
        }
        
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => {
                this.nextSlide();
            });
        }
        
        // Pause auto-slide on hover
        if (this.carousel.parentElement) {
            this.carousel.parentElement.addEventListener('mouseenter', () => {
                this.stopAutoSlide();
            });
            
            this.carousel.parentElement.addEventListener('mouseleave', () => {
                this.startAutoSlide();
            });
        }
        
        // Touch/swipe support
        this.addTouchSupport();
        
        // Keyboard navigation
        this.addKeyboardSupport();
    }
    
    addTouchSupport() {
        let startX = 0;
        let endX = 0;
        
        this.carousel.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        });
        
        this.carousel.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            this.handleSwipe(startX, endX);
        });
    }
    
    handleSwipe(startX, endX) {
        const threshold = 50; // Minimum swipe distance
        const diff = startX - endX;
        
        if (Math.abs(diff) > threshold) {
            if (diff > 0) {
                this.nextSlide(); // Swipe left - next slide
            } else {
                this.prevSlide(); // Swipe right - previous slide
            }
        }
    }
    
    addKeyboardSupport() {
        document.addEventListener('keydown', (e) => {
            if (this.isCarouselInView()) {
                switch(e.key) {
                    case 'ArrowLeft':
                        e.preventDefault();
                        this.prevSlide();
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        this.nextSlide();
                        break;
                }
            }
        });
    }
    
    isCarouselInView() {
        const rect = this.carousel.getBoundingClientRect();
        return rect.top < window.innerHeight && rect.bottom > 0;
    }
    
    prevSlide() {
        const totalSlides = Math.ceil(this.totalCards / this.cardsPerView);
        this.currentIndex = this.currentIndex > 0 ? this.currentIndex - 1 : totalSlides - 1;
        this.updateCarousel();
        this.updateIndicators();
        this.restartAutoSlide();
    }
    
    nextSlide() {
        const totalSlides = Math.ceil(this.totalCards / this.cardsPerView);
        this.currentIndex = this.currentIndex < totalSlides - 1 ? this.currentIndex + 1 : 0;
        this.updateCarousel();
        this.updateIndicators();
        this.restartAutoSlide();
    }
    
    goToSlide(index) {
        this.currentIndex = index;
        this.updateCarousel();
        this.updateIndicators();
        this.restartAutoSlide();
    }
    
    updateCarousel() {
        if (!this.carousel) return;
        
        const cardWidth = 100 / this.cardsPerView;
        const translateX = -this.currentIndex * 100;
        
        this.carousel.style.transform = `translateX(${translateX}%)`;
        
        // Add animation class
        this.carousel.classList.add('auto-sliding');
        setTimeout(() => {
            this.carousel.classList.remove('auto-sliding');
        }, 500);
    }
    
    updateIndicators() {
        if (!this.indicatorsContainer) return;
        
        const indicators = this.indicatorsContainer.querySelectorAll('.carousel-indicator');
        indicators.forEach((indicator, index) => {
            indicator.classList.toggle('active', index === this.currentIndex);
        });
    }
    
    startAutoSlide() {
        this.stopAutoSlide(); // Clear any existing interval
        
        this.autoSlideInterval = setInterval(() => {
            this.nextSlide();
        }, this.autoSlideDelay);
    }
    
    stopAutoSlide() {
        if (this.autoSlideInterval) {
            clearInterval(this.autoSlideInterval);
            this.autoSlideInterval = null;
        }
    }
    
    restartAutoSlide() {
        this.stopAutoSlide();
        this.startAutoSlide();
    }
    
    // Public method to destroy the carousel
    destroy() {
        this.stopAutoSlide();
        
        // Remove event listeners
        window.removeEventListener('resize', this.updateCardsPerView);
        
        if (this.prevBtn) {
            this.prevBtn.removeEventListener('click', this.prevSlide);
        }
        
        if (this.nextBtn) {
            this.nextBtn.removeEventListener('click', this.nextSlide);
        }
    }
}

// Initialize carousel when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit to ensure all styles are loaded
    setTimeout(() => {
        window.servicesCarousel = new ServicesCarousel();
    }, 100);
});

// Handle page visibility change to pause/resume auto-slide
document.addEventListener('visibilitychange', () => {
    if (window.servicesCarousel) {
        if (document.hidden) {
            window.servicesCarousel.stopAutoSlide();
        } else {
            window.servicesCarousel.startAutoSlide();
        }
    }
});

// Intersection Observer for performance optimization
if ('IntersectionObserver' in window) {
    const carouselObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (window.servicesCarousel) {
                if (entry.isIntersecting) {
                    window.servicesCarousel.startAutoSlide();
                } else {
                    window.servicesCarousel.stopAutoSlide();
                }
            }
        });
    }, {
        threshold: 0.5
    });
    
    document.addEventListener('DOMContentLoaded', () => {
        const servicesSection = document.getElementById('services');
        if (servicesSection) {
            carouselObserver.observe(servicesSection);
        }
    });
}

