let currentQvProduct = null;

function getStoredWishlist() {
    try {
        return JSON.parse(localStorage.getItem('islington_wishlist')) || [];
    } catch (e) {
        return [];
    }
}

function setStoredWishlist(items) {
    localStorage.setItem('islington_wishlist', JSON.stringify(items));
    updateWishlistBadges();
}

function updateWishlistBadges() {
    const items = getStoredWishlist();
    const badge = document.getElementById('wishlistCountBadge');
    if (badge) {
        badge.innerText = items.length;
    }
}

function toggleWishlist(productId, name, price, img, category) {
    let items = getStoredWishlist();
    const existingIndex = items.findIndex(i => String(i.id) === String(productId));

    if (existingIndex > -1) {
        items.splice(existingIndex, 1);
        setStoredWishlist(items);
        showSiteToast(`Removed "${name}" from your wishlist.`, false);
        updateWishlistHeartUI(productId, false);
    } else {
        items.push({ id: productId, name, price, img, category });
        setStoredWishlist(items);
        showSiteToast(`Added "${name}" to your wishlist!`, true);
        updateWishlistHeartUI(productId, true);
    }
}

function updateWishlistHeartUI(productId, isWishlisted) {
    const heartBtns = document.querySelectorAll(`.wishlist-toggle-btn[data-id="${productId}"]`);
    heartBtns.forEach(btn => {
        const icon = btn.querySelector('i');
        if (icon) {
            if (isWishlisted) {
                icon.className = 'fa fa-heart text-danger';
            } else {
                icon.className = 'far fa-heart';
            }
        }
    });
}

function toggleWishlistModal() {
    const container = document.getElementById('wishlistItemsContainer');
    const items = getStoredWishlist();
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="far fa-heart text-muted display-4 d-block mb-3"></i>
                <h6 class="fw-bold text-dark">Your Wishlist is Empty</h6>
                <p class="text-muted small">Save items you like while browsing our marketplace!</p>
                <a href="/products/" class="btn btn-primary btn-sm rounded mt-2">Explore Items</a>
            </div>
        `;
    } else {
        container.innerHTML = items.map(item => `
            <div class="card border rounded p-2 shadow-sm d-flex flex-row align-items-center gap-3">
                <img src="${item.img || '/static/images/default.jpg'}" class="rounded object-fit-cover" style="width: 55px; height: 55px;" alt="${item.name}">
                <div class="flex-grow-1 overflow-hidden">
                    <h6 class="mb-1 text-truncate fw-bold small">${item.name}</h6>
                    <span class="text-primary fw-bold small">Rs. ${parseFloat(item.price).toLocaleString()}</span>
                </div>
                <div class="d-flex flex-column gap-1">
                    <a href="/products/${item.id}/" class="btn btn-sm btn-outline-primary px-2" title="View"><i class="fa fa-eye"></i></a>
                    <button type="button" class="btn btn-sm btn-outline-danger px-2" onclick="toggleWishlist('${item.id}', '${item.name.replace(/'/g, "\\'")}', ${item.price}, '${item.img}', '${item.category}'); toggleWishlistModal();" title="Remove"><i class="fa fa-trash"></i></button>
                </div>
            </div>
        `).join('');
    }

    const offcanvasEl = document.getElementById('wishlistOffcanvas');
    if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        offcanvas.show();
    }
}

function clearAllWishlist() {
    setStoredWishlist([]);
    toggleWishlistModal();
    showSiteToast('Wishlist cleared.', false);
    document.querySelectorAll('.wishlist-toggle-btn i').forEach(i => i.className = 'far fa-heart');
}

function getStoredCart() {
    try {
        return JSON.parse(localStorage.getItem('islington_cart')) || [];
    } catch (e) {
        return [];
    }
}

function setStoredCart(items) {
    localStorage.setItem('islington_cart', JSON.stringify(items));
    updateCartBadges();
}

function updateCartBadges() {
    const items = getStoredCart();
    const badge = document.getElementById('cartCountBadge');
    if (badge) {
        badge.innerText = items.length;
    }
}

function toggleCart(productId, name, price, img) {
    let items = getStoredCart();
    const existing = items.find(i => String(i.id) === String(productId));
    if (existing) {
        existing.qty = (existing.qty || 1) + 1;
        showSiteToast(`Updated quantity for "${name}" in your bag!`, true);
    } else {
        items.push({ id: productId, name, price: parseFloat(price) || 0, img, qty: 1 });
        showSiteToast(`Added "${name}" to your shopping bag!`, true);
    }
    setStoredCart(items);
}

function toggleCartDrawer() {
    const container = document.getElementById('cartItemsContainer');
    const items = getStoredCart();
    let total = 0;
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="fa fa-shopping-cart text-muted display-4 d-block mb-3"></i>
                <h6 class="fw-bold text-dark">Your Bag is Empty</h6>
                <p class="text-muted small">Add products from our marketplace to meet up and buy.</p>
                <a href="/products/" class="btn btn-primary btn-sm rounded mt-2">Browse Store</a>
            </div>
        `;
        const totalEl = document.getElementById('cartTotalSum');
        if (totalEl) totalEl.innerText = 'Rs. 0.00';
    } else {
        container.innerHTML = items.map((item, idx) => {
            const itemPrice = parseFloat(item.price) || 0;
            const itemQty = parseInt(item.qty) || 1;
            total += (itemPrice * itemQty);
            return `
                <div class="card border rounded p-2 shadow-sm d-flex flex-row align-items-center gap-3">
                    <img src="${item.img || '/static/images/default.jpg'}" class="rounded object-fit-cover" style="width: 55px; height: 55px;" alt="${item.name}">
                    <div class="flex-grow-1 overflow-hidden">
                        <h6 class="mb-1 text-truncate fw-bold small">${item.name}</h6>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-primary fw-bold small">Rs. ${itemPrice.toLocaleString()} &times; ${itemQty}</span>
                            <span class="fw-bold small text-dark">Rs. ${(itemPrice * itemQty).toLocaleString()}</span>
                        </div>
                    </div>
                    <button type="button" class="btn btn-sm text-danger" onclick="removeCartItem(${idx})"><i class="fa fa-times-circle fs-5"></i></button>
                </div>
            `;
        }).join('');
        const totalEl = document.getElementById('cartTotalSum');
        if (totalEl) totalEl.innerText = 'Rs. ' + total.toLocaleString();
    }

    const offcanvasEl = document.getElementById('cartOffcanvas');
    if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        offcanvas.show();
    }
}

function removeCartItem(idx) {
    let items = getStoredCart();
    items.splice(idx, 1);
    setStoredCart(items);
    toggleCartDrawer();
    showSiteToast('Item removed from your bag.', false);
}

function clearAllCart() {
    setStoredCart([]);
    toggleCartDrawer();
    showSiteToast('Shopping bag cleared.', false);
}

function handleCheckoutModal() {
    const items = getStoredCart();
    if (items.length === 0) {
        showSiteToast('Please add items to your bag first!', false);
        return;
    }
    showSiteToast('Campus meetup scheduled! Contact seller at Islington hub.', true);
    clearAllCart();
}

function openQuickView(id, name, price, img, category, desc, stock, detailUrl) {
    currentQvProduct = { id, name, price, img, category, desc, stock, detailUrl };

    const titleEl = document.getElementById('qvProductTitle');
    const priceEl = document.getElementById('qvProductPrice');
    const imgEl = document.getElementById('qvProductImg');
    const catEl = document.getElementById('qvProductCategory');
    const descEl = document.getElementById('qvProductDescription');

    if (titleEl) titleEl.innerText = name;
    if (priceEl) priceEl.innerText = 'Rs. ' + parseFloat(price).toLocaleString();
    if (imgEl) imgEl.src = img || '/static/images/default.jpg';
    if (catEl) catEl.innerText = category || 'General';
    if (descEl) descEl.innerText = desc || 'No description provided for this item.';

    const stockBadge = document.getElementById('qvProductStockBadge');
    const addBtn = document.getElementById('qvAddToCartBtn');
    if (stockBadge && addBtn) {
        if (parseInt(stock) > 0) {
            stockBadge.className = 'badge bg-success-subtle text-success border border-success-subtle';
            stockBadge.innerText = `In Stock (${stock} available)`;
            addBtn.disabled = false;
            addBtn.className = 'btn btn-primary flex-grow-1 py-2 fw-semibold';
        } else {
            stockBadge.className = 'badge bg-danger-subtle text-danger border border-danger-subtle';
            stockBadge.innerText = 'Sold Out';
            addBtn.disabled = true;
            addBtn.className = 'btn btn-secondary flex-grow-1 py-2 fw-semibold';
        }
    }

    const fullLink = document.getElementById('qvFullDetailLink');
    if (fullLink) fullLink.href = detailUrl || `/products/${id}/`;

    const wishlist = getStoredWishlist();
    const isWishlisted = wishlist.some(i => String(i.id) === String(id));
    const qvIcon = document.getElementById('qvWishlistIcon');
    if (qvIcon) {
        qvIcon.className = isWishlisted ? 'fa fa-heart text-danger' : 'far fa-heart';
    }

    const modalEl = document.getElementById('quickViewModal');
    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

function handleQuickAddToCart() {
    if (currentQvProduct) {
        toggleCart(currentQvProduct.id, currentQvProduct.name, currentQvProduct.price, currentQvProduct.img);
    }
}

function handleQuickWishlistToggle() {
    if (currentQvProduct) {
        toggleWishlist(currentQvProduct.id, currentQvProduct.name, currentQvProduct.price, currentQvProduct.img, currentQvProduct.category);
        const wishlist = getStoredWishlist();
        const isWishlisted = wishlist.some(i => String(i.id) === String(currentQvProduct.id));
        const qvIcon = document.getElementById('qvWishlistIcon');
        if (qvIcon) qvIcon.className = isWishlisted ? 'fa fa-heart text-danger' : 'far fa-heart';
    }
}

function showSiteToast(message, isSuccess = true) {
    const toastEl = document.getElementById('siteToast');
    const toastBody = document.getElementById('siteToastBody');
    if (!toastEl || !toastBody) return;

    toastEl.className = `toast align-items-center text-white border-0 shadow-lg rounded-3 ${isSuccess ? 'bg-dark' : 'bg-danger'}`;
    toastBody.innerHTML = `<i class="fa ${isSuccess ? 'fa-check-circle text-success' : 'fa-exclamation-triangle text-warning'} fs-5"></i> <span>${message}</span>`;

    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function copyProductLink(urlPath, productName) {
    const fullUrl = window.location.origin + urlPath;
    navigator.clipboard.writeText(fullUrl).then(() => {
        showSiteToast(`Copied share link for "${productName}"!`, true);
    }).catch(() => {
        showSiteToast(`Link: ${fullUrl}`, true);
    });
}

function handleNewsletterSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('newsletterEmailInput');
    if (input && input.value) {
        showSiteToast(`Welcome to the club! You are subscribed as ${input.value}`, true);
        input.value = '';
    }
}

function filterByCat(catName, btnElement) {
    const buttons = document.querySelectorAll('#categoryFilterBar button');
    buttons.forEach(b => {
        b.className = 'btn btn-sm btn-light border rounded-pill px-3 fw-semibold text-muted';
    });
    if (btnElement) {
        btnElement.className = 'btn btn-sm btn-primary rounded-pill px-3 fw-semibold';
    }

    const items = document.querySelectorAll('#productGridContainer .product-card-col');
    const emptyMsg = document.getElementById('filterEmptyMessage');
    let visible = 0;

    items.forEach(item => {
        const itemCat = item.dataset.category || '';
        const inStock = item.dataset.instock === 'true';

        let match = false;
        if (catName === 'all') {
            match = true;
        } else if (catName === 'instock') {
            match = inStock;
        } else {
            match = itemCat.includes(catName);
        }

        if (match) {
            item.classList.remove('d-none');
            visible++;
        } else {
            item.classList.add('d-none');
        }
    });

    if (emptyMsg) {
        if (visible === 0 && items.length > 0) {
            emptyMsg.classList.remove('d-none');
        } else {
            emptyMsg.classList.add('d-none');
        }
    }
}

window.addEventListener('scroll', function () {
    const btn = document.getElementById('backToTopBtn');
    if (btn) {
        if (window.scrollY > 300) {
            btn.classList.add('visible');
        } else {
            btn.classList.remove('visible');
        }
    }
});

/* ==========================================================================
   Campus Chat System (AI Support & Seller Inquiry Engine)
   ========================================================================== */

const CHAT_STORAGE_KEY = 'islington_campus_chat_history';

function getStoredChatMessages() {
    try {
        const stored = localStorage.getItem(CHAT_STORAGE_KEY);
        if (stored) {
            let parsed = JSON.parse(stored);
            // Sanitize legacy stored messages with admin links
            parsed = parsed.map(m => {
                if (m.text && m.text.includes('/admin/products/product/add/')) {
                    m.text = m.text.replace(/\/admin\/products\/product\/add\//g, '/profile/?tab=add');
                }
                return m;
            });
            return parsed;
        }
    } catch (e) { }

    return [
        {
            id: 1,
            sender: 'assistant',
            text: 'Hello student! 👋 Welcome to Islington Marketplace. How can I help you today? You can ask about campus meetup spots, safe payments, or how to sell an item.',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
    ];
}

function setStoredChatMessages(msgs) {
    try {
        localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(msgs));
    } catch (e) { }
    renderChatMessages();
}

function renderChatMessages() {
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;

    const msgs = getStoredChatMessages();
    container.innerHTML = msgs.map(m => {
        let productCardHtml = '';
        if (m.product) {
            productCardHtml = `
                <div class="chat-product-preview-card">
                    <img src="${m.product.img || '/static/images/default.jpg'}" alt="${m.product.name}">
                    <div class="overflow-hidden">
                        <div class="fw-bold small text-truncate">${m.product.name}</div>
                        <span class="text-primary fw-bold small">Rs. ${parseFloat(m.product.price).toLocaleString()}</span>
                    </div>
                </div>
            `;
        }

        return `
            <div class="chat-bubble ${m.sender}">
                ${productCardHtml}
                <div>${m.text}</div>
                <span class="chat-bubble-time">${m.time || ''}</span>
            </div>
        `;
    }).join('');

    container.scrollTop = container.scrollHeight;
}

function toggleCampusChat() {
    const chatWin = document.getElementById('campusChatWindow');
    if (!chatWin) return;

    chatWin.classList.toggle('active');
    if (chatWin.classList.contains('active')) {
        renderChatMessages();
        const input = document.getElementById('chatTextInput');
        if (input) setTimeout(() => input.focus(), 150);
    }
}

function clearCampusChat() {
    localStorage.removeItem(CHAT_STORAGE_KEY);
    renderChatMessages();
    showSiteToast('Chat conversation cleared.', true);
}

function sendQuickPrompt(promptText) {
    addChatMessage('user', promptText);
    triggerAssistantReply(promptText);
}

function handleChatSubmit(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('chatTextInput');
    if (!input || !input.value.trim()) return;

    const text = input.value.trim();
    input.value = '';
    addChatMessage('user', text);
    triggerAssistantReply(text);
}

function addChatMessage(sender, text, product = null) {
    const msgs = getStoredChatMessages();
    msgs.push({
        id: Date.now(),
        sender,
        text,
        product,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });
    setStoredChatMessages(msgs);
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessagesContainer');
    if (!container) return;

    const typingEl = document.createElement('div');
    typingEl.id = 'chatTypingIndicator';
    typingEl.className = 'chat-typing-indicator';
    typingEl.innerHTML = `
        <div class="chat-typing-dot"></div>
        <div class="chat-typing-dot"></div>
        <div class="chat-typing-dot"></div>
    `;
    container.appendChild(typingEl);
    container.scrollTop = container.scrollHeight;
}

function hideTypingIndicator() {
    const typingEl = document.getElementById('chatTypingIndicator');
    if (typingEl) typingEl.remove();
}

function triggerAssistantReply(userQuery, productContext = null) {
    showTypingIndicator();

    setTimeout(() => {
        hideTypingIndicator();
        let reply = '';
        const q = userQuery.toLowerCase();

        if (q.includes('meetup') || q.includes('where') || q.includes('location') || q.includes('spot')) {
            reply = '📍 Designated safe handover spots on campus: **Block C Library Lobby** and **Ground Floor Cafeteria**. Always meet inside campus and inspect the item first!';
        } else if (q.includes('pay') || q.includes('esewa') || q.includes('khalti') || q.includes('money') || q.includes('cash') || q.includes('safety')) {
            reply = '🛡️ **Payment Guideline:** We recommend paying on the spot via Cash, eSewa, or Khalti *after* you physically inspect the item during the campus meetup.';
        } else if (q.includes('sell') || q.includes('list') || q.includes('post') || q.includes('upload')) {
            reply = '📦 To sell an item, click **"Sell an Item"** in the top navigation or go to your student dashboard at `/profile/?tab=add`. You can upload photos, set prices, and manage stock directly from your profile!';
        } else if (q.includes('price') || q.includes('negotiate') || q.includes('discount') || q.includes('offer')) {
            reply = '🤝 Many student sellers are happy to negotiate! Use this chat to send offers, bundle multiple textbooks, or request friendly student discounts.';
        } else if (q.includes('hello') || q.includes('hi') || q.includes('hey')) {
            reply = 'Hey there! 😊 How can I help you with your campus shopping or selling today?';
        } else if (productContext) {
            reply = `Thanks for asking about **${productContext.name}**! The seller has been notified. Would you like to schedule a meetup at the Library lobby?`;
        } else {
            reply = 'Got your message! A fellow Islington peer or support team member will assist you shortly. In the meantime, feel free to browse our store or check safety guidelines!';
        }

        addChatMessage('assistant', reply);
    }, 1000);
}

function openProductChat(productName, productPrice, productImg) {
    const chatWin = document.getElementById('campusChatWindow');
    if (!chatWin) return;

    if (!chatWin.classList.contains('active')) {
        chatWin.classList.add('active');
    }

    const inquiryText = `Hi! I'm interested in buying this item. Is it still available for a campus meetup?`;
    const productData = { name: productName, price: productPrice, img: productImg };

    addChatMessage('user', inquiryText, productData);
    triggerAssistantReply(inquiryText, productData);
}

document.addEventListener('DOMContentLoaded', function () {
    updateWishlistBadges();
    updateCartBadges();
    const wishlist = getStoredWishlist();
    wishlist.forEach(item => {
        updateWishlistHeartUI(item.id, true);
    });
    renderChatMessages();
    // Start notification polling
    fetchNotifications();
    setInterval(fetchNotifications, 5000);
});


/* ==========================================================================
   NOTIFICATION SYSTEM - AJAX POLLING ENGINE
   ========================================================================== */

function fetchNotifications() {
    const badge = document.getElementById('notifCountBadge');
    const body = document.getElementById('notifDropdownBody');
    if (!badge || !body) return; // Not logged in

    fetch('/api/notifications/', {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(res => res.json())
    .then(data => {
        // Update badge count
        if (data.unread_count > 0) {
            badge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }

        // Render notification items
        if (data.notifications.length === 0) {
            body.innerHTML = `
                <div class="text-center text-muted py-4 small">
                    <i class="fa fa-bell-slash d-block mb-2" style="font-size:1.5rem;"></i>
                    No notifications yet
                </div>`;
            return;
        }

        let html = '';
        data.notifications.forEach(n => {
            const readClass = n.is_read ? '' : 'unread';
            html += `
                <div class="notif-item ${readClass}" data-id="${n.id}" onclick="handleNotifClick(${n.id}, '${n.link}', ${n.is_read})">
                    <div class="notif-item-icon notif-icon-${n.type}">
                        <i class="fa ${n.icon}"></i>
                    </div>
                    <div class="notif-item-content">
                        <div class="notif-item-title">${n.title}</div>
                        ${n.message ? `<div class="notif-item-msg">${n.message}</div>` : ''}
                        <div class="notif-item-time">${n.time_ago}</div>
                    </div>
                    ${!n.is_read ? '<div class="notif-unread-dot"></div>' : ''}
                </div>`;
        });
        body.innerHTML = html;
    })
    .catch(() => {});
}

function toggleNotifPanel() {
    const panel = document.getElementById('notifDropdownPanel');
    if (!panel) return;
    panel.classList.toggle('active');
}

function handleNotifClick(id, link, isRead) {
    // Mark as read
    if (!isRead) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        const formData = new FormData();
        formData.append('id', id);
        if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken.value);

        fetch('/api/notifications/read/', {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then(() => fetchNotifications());
    }

    // Navigate if link exists
    if (link) {
        window.location.href = link;
    }
}

function markAllNotifRead(event) {
    event.stopPropagation();
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    const formData = new FormData();
    if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken.value);

    fetch('/api/notifications/read-all/', {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    }).then(() => fetchNotifications());
}

// Close notification panel when clicking outside
document.addEventListener('click', function(e) {
    const panel = document.getElementById('notifDropdownPanel');
    const bell = document.getElementById('notifBellWrap');
    if (panel && bell && !bell.contains(e.target)) {
        panel.classList.remove('active');
    }
});
