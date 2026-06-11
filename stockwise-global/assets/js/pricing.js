/**
 * StockWise - Pricing Page JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // Billing toggle
    const billingToggle = document.getElementById('billingToggle');
    const priceAmounts = document.querySelectorAll('.price .amount');
    const monthlyLabel = document.querySelector('.billing-toggle span:first-child');
    const yearlyLabel = document.querySelector('.billing-toggle span:last-child');

    billingToggle?.addEventListener('change', () => {
        const isYearly = billingToggle.checked;

        // Update labels
        monthlyLabel.classList.toggle('active', !isYearly);
        yearlyLabel.classList.toggle('active', isYearly);

        // Update prices
        priceAmounts.forEach(amount => {
            const price = isYearly ? amount.dataset.yearly : amount.dataset.monthly;
            if (price) {
                amount.textContent = price;
            }
        });
    });

    // FAQ accordion
    const faqItems = document.querySelectorAll('.faq-item');

    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            
            // Close all
            faqItems.forEach(i => i.classList.remove('active'));
            
            // Open clicked if it wasn't active
            if (!isActive) {
                item.classList.add('active');
            }
        });
    });

    // Plan buttons
    document.querySelectorAll('.btn-plan').forEach(btn => {
        btn.addEventListener('click', () => {
            const plan = btn.closest('.pricing-card').querySelector('h3').textContent;
            
            if (plan === 'Enterprise') {
                alert('Please contact our sales team for Enterprise plans.');
            } else {
                alert(`Thank you for choosing the ${plan} plan! Redirecting to checkout...`);
            }
        });
    });
});
