document.addEventListener("DOMContentLoaded", function() {
    const carouselTrack = document.querySelector(".clients-carousel-track");
    if (carouselTrack) {
        // Duplicate the logos to create a seamless loop
        const logos = Array.from(carouselTrack.children);
        logos.forEach(logo => {
            carouselTrack.appendChild(logo.cloneNode(true));
        });
    }
});


