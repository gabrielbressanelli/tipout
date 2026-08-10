const toastRegion = document.querySelector('.toast-region');

if (toastRegion) {
    const dismissToast = (toast) => {
        toast.classList.remove('is-visible');
        toast.classList.add('is-leaving');
        window.setTimeout(() => toast.remove(), 240);
    };

    toastRegion.querySelectorAll('.toast').forEach((toast) => {
        const timeout = Number(toast.dataset.timeout || 4000);
        const timer = toast.querySelector('.toast-timer');
        const closeButton = toast.querySelector('.toast-close');

        if (timer) {
            timer.style.setProperty('--toast-duration', `${timeout}ms`);
        }

        window.requestAnimationFrame(() => {
            toast.classList.add('is-visible');
        });

        const dismissalTimer = window.setTimeout(() => dismissToast(toast), timeout);

        closeButton?.addEventListener('click', () => {
            window.clearTimeout(dismissalTimer);
            dismissToast(toast);
        });
    });
}
