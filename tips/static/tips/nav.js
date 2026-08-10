const menuToggle = document.querySelector('.menu-toggle');
const navDrawer = document.querySelector('#primary-nav');
const navCloseControls = document.querySelectorAll('[data-nav-close]');

if (menuToggle && navDrawer) {
    const setMenuOpen = (isOpen) => {
        document.body.classList.toggle('nav-open', isOpen);
        menuToggle.setAttribute('aria-expanded', String(isOpen));
    };

    menuToggle.addEventListener('click', () => {
        setMenuOpen(!document.body.classList.contains('nav-open'));
    });

    navCloseControls.forEach((control) => {
        control.addEventListener('click', () => setMenuOpen(false));
    });

    navDrawer.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => setMenuOpen(false));
    });

    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            setMenuOpen(false);
        }
    });
}
