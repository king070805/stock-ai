/**
 * StockWise - PayPal Payment Integration
 * Handles PayPal subscription payments
 */

// PayPal SDK Configuration
const PAYPAL_CONFIG = {
    clientId: 'YOUR_PAYPAL_CLIENT_ID', // Replace with your PayPal Client ID
    currency: 'USD',
    intent: 'subscription',
    vault: true
};

// Subscription Plans
const SUBSCRIPTION_PLANS = {
    pro: {
        name: 'StockWise Pro',
        description: 'Advanced AI stock analysis with real-time alerts',
        monthly: {
            price: '19.99',
            planId: 'YOUR_MONTHLY_PLAN_ID' // Replace with PayPal Plan ID
        },
        yearly: {
            price: '199.99',
            planId: 'YOUR_YEARLY_PLAN_ID' // Replace with PayPal Plan ID
        }
    },
    enterprise: {
        name: 'StockWise Enterprise',
        description: 'Unlimited AI analysis with API access',
        monthly: {
            price: '49.99',
            planId: 'YOUR_ENTERPRISE_MONTHLY_PLAN_ID'
        },
        yearly: {
            price: '499.99',
            planId: 'YOUR_ENTERPRISE_YEARLY_PLAN_ID'
        }
    }
};

// Initialize PayPal Button
function initPayPalButton(planType, billingCycle) {
    const plan = SUBSCRIPTION_PLANS[planType];
    if (!plan) {
        console.error('Invalid plan type:', planType);
        return;
    }

    const planConfig = plan[billingCycle];

    paypal.Buttons({
        style: {
            shape: 'rect',
            color: 'gold',
            layout: 'vertical',
            label: 'subscribe'
        },
        createSubscription: function(data, actions) {
            return actions.subscription.create({
                plan_id: planConfig.planId
            });
        },
        onApprove: function(data, actions) {
            // Subscription approved
            console.log('Subscription approved:', data);
            handleSubscriptionSuccess(data, planType, billingCycle);
        },
        onCancel: function(data) {
            // Subscription cancelled
            console.log('Subscription cancelled:', data);
            showNotification('Subscription cancelled. You can try again anytime.', 'info');
        },
        onError: function(err) {
            // Error occurred
            console.error('PayPal error:', err);
            showNotification('Payment failed. Please try again.', 'error');
        }
    }).render(`#paypal-button-${planType}`);
}

// Handle successful subscription
function handleSubscriptionSuccess(data, planType, billingCycle) {
    // Send subscription data to your server
    fetch('/api/subscription/activate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            subscriptionId: data.subscriptionID,
            planType: planType,
            billingCycle: billingCycle,
            userId: getCurrentUserId()
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('Subscription activated successfully!', 'success');
            // Redirect to dashboard or update UI
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 2000);
        } else {
            showNotification('Failed to activate subscription. Please contact support.', 'error');
        }
    })
    .catch(error => {
        console.error('Error activating subscription:', error);
        showNotification('An error occurred. Please contact support.', 'error');
    });
}

// Cancel subscription
function cancelSubscription(subscriptionId) {
    if (!confirm('Are you sure you want to cancel your subscription?')) {
        return;
    }

    fetch('/api/subscription/cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            subscriptionId: subscriptionId,
            userId: getCurrentUserId()
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification('Subscription cancelled successfully.', 'success');
            // Update UI
            updateSubscriptionUI('free');
        } else {
            showNotification('Failed to cancel subscription. Please try again.', 'error');
        }
    })
    .catch(error => {
        console.error('Error cancelling subscription:', error);
        showNotification('An error occurred. Please try again.', 'error');
    });
}

// Get current user ID (placeholder - implement based on your auth system)
function getCurrentUserId() {
    // This should return the current logged-in user's ID
    // For now, return from localStorage or session
    return localStorage.getItem('userId') || 'guest';
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    // Color based on type
    const colors = {
        success: '#2d8a4e',
        error: '#c0392b',
        info: '#1a2744',
        warning: '#d4a017'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Update subscription UI
function updateSubscriptionUI(plan) {
    const planElements = document.querySelectorAll('[data-plan]');
    planElements.forEach(el => {
        if (el.dataset.plan === plan) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
}

// Check subscription status
async function checkSubscriptionStatus() {
    try {
        const response = await fetch(`/api/subscription/status?userId=${getCurrentUserId()}`);
        const data = await response.json();
        
        if (data.active) {
            updateSubscriptionUI(data.plan);
            return data.plan;
        } else {
            updateSubscriptionUI('free');
            return 'free';
        }
    } catch (error) {
        console.error('Error checking subscription:', error);
        return 'free';
    }
}

// Initialize PayPal SDK
function loadPayPalSDK() {
    return new Promise((resolve, reject) => {
        if (document.getElementById('paypal-sdk')) {
            resolve();
            return;
        }
        
        const script = document.createElement('script');
        script.id = 'paypal-sdk';
        script.src = `https://www.paypal.com/sdk/js?client-id=${PAYPAL_CONFIG.clientId}&vault=true&intent=subscription`;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initPayPalButton,
        cancelSubscription,
        checkSubscriptionStatus,
        loadPayPalSDK,
        SUBSCRIPTION_PLANS
    };
}
