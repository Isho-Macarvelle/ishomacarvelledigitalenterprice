const productList = document.getElementById('product-list');
const cartList = document.getElementById('cart-list');
const cartTotal = document.getElementById('cart-total');
const searchInput = document.getElementById('search-input');
const categorySelect = document.getElementById('category-select');
const productModal = document.getElementById('product-modal');
const modalImage = document.getElementById('modal-image');
const modalTitle = document.getElementById('modal-title');
const modalCategory = document.getElementById('modal-category');
const modalDescription = document.getElementById('modal-description');
const modalPrice = document.getElementById('modal-price');
const modalStock = document.getElementById('modal-stock');
const modalRating = document.getElementById('modal-rating');
const reviewSortSelect = document.getElementById('review-sort');
const reviewList = document.getElementById('review-list');
const reviewForm = document.getElementById('review-form');
const reviewLoginHint = document.getElementById('review-login-hint');
const reviewRatingInput = document.getElementById('review-rating');
const reviewCommentInput = document.getElementById('review-comment');
const modalAddButton = document.getElementById('modal-add-button');
const orderModal = document.getElementById('order-modal');
const orderModalContent = document.getElementById('order-modal-content');
const orderDetailsBody = document.getElementById('order-details-body');
const orderDetailsInfo = document.getElementById('order-details-info');
const persistenceStatus = document.getElementById('persistence-status');
const seedButton = document.getElementById('seed-button');
const toastContainer = document.getElementById('toast-container');
const cartBadge = document.getElementById('cart-badge');
const authModal = document.getElementById('auth-modal');
const authForm = document.getElementById('auth-form');
const authNameInput = document.getElementById('auth-name');
const authEmailInput = document.getElementById('auth-email');
const authPasswordInput = document.getElementById('auth-password');
const authTitle = document.getElementById('auth-title');
const authSubmitBtn = document.getElementById('auth-submit-btn');
const authToggle = document.getElementById('auth-toggle');
const userMenu = document.getElementById('user-menu');
const adminModal = document.getElementById('admin-modal');
const adminProductsBody = document.getElementById('admin-products-body');
const adminProductForm = document.getElementById('admin-product-form');
const checkoutModal = document.getElementById('checkout-modal');
const checkoutForm = document.getElementById('checkout-form');
const checkoutSummary = document.getElementById('checkout-summary');
const shippingCostDisplay = document.getElementById('shipping-cost-display');
const cardErrorsDiv = document.getElementById('card-errors');
const analyticsModal = document.getElementById('analytics-modal');

let productCache = [];
let selectedProductId = null;
let currentUser = null;
let isSignupMode = false;
let stripe = null;
let cardElement = null;
let currentShippingCost = 9.99;
let revenueChart = null;
let dailyRevenueChart = null;

// Initialize Stripe
async function initializeStripe() {
  // Fetch publishable key from backend (optional - we'll use placeholder for demo)
  stripe = Stripe('pk_test_placeholder_key_DO_NOT_USE_IN_PRODUCTION');
  const elements = stripe.elements();
  cardElement = elements.create('card');
}

async function fetchProducts(search = '', category = '') {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (category) params.set('category', category);
  const qs = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`/api/products${qs}`);
  return await res.json();
}

async function fetchCategories() {
  const res = await fetch('/api/categories');
  return await res.json();
}

async function fetchCart() {
  const res = await fetch('/api/cart');
  return await res.json();
}

async function fetchOrders() {
  const res = await fetch('/api/orders');
  return await res.json();
}

async function fetchReviews(productId) {
  const sort = reviewSortSelect ? reviewSortSelect.value : 'newest';
  const params = new URLSearchParams({sort});
  const res = await fetch(`/api/products/${productId}/reviews?${params.toString()}`);
  return res.ok ? await res.json() : [];
}

async function postReview(productId, rating, comment) {
  const res = await fetch(`/api/products/${productId}/reviews`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({rating, comment}),
  });
  return await res.json();
}

function renderReviewStars(rating) {
  return '★'.repeat(rating) + '☆'.repeat(5 - rating);
}

async function renderProductReviews(productId) {
  if (reviewSortSelect) {
    reviewSortSelect.value = reviewSortSelect.value || 'newest';
  }
  const reviews = await fetchReviews(productId);
  if (reviews.length === 0) {
    reviewList.innerHTML = '<p style="color:#666;">No reviews yet. Be the first to review this product.</p>';
  } else {
    reviewList.innerHTML = '<div class="review-list">' + reviews.map(review => `
      <div class="review-item">
        <strong>${review.user_name}</strong>
        <div class="review-rating">${renderReviewStars(review.rating)} (${review.rating}/5)</div>
        <p>${review.comment}</p>
      </div>
    `).join('') + '</div>';
  }

  if (currentUser) {
    reviewForm.classList.remove('hidden');
    reviewLoginHint.classList.add('hidden');
  } else {
    reviewForm.classList.add('hidden');
    reviewLoginHint.classList.remove('hidden');
  }
}

async function submitReview() {
  if (!selectedProductId) return;
  const rating = Number(reviewRatingInput.value);
  const comment = reviewCommentInput.value.trim();
  if (!comment) {
    showToast('Please write a comment for your review.', 'warning');
    return;
  }
  const result = await postReview(selectedProductId, rating, comment);
  if (result.error) {
    showToast(result.error, 'error');
    return;
  }
  showToast('Review posted successfully.', 'success');
  reviewCommentInput.value = '';
  await renderProducts(searchInput.value.trim(), categorySelect.value);
  await showProductDetails(selectedProductId);
}

function setReviewSort(event) {
  if (!selectedProductId) return;
  renderProductReviews(selectedProductId);
}

async function getCurrentUser() {
  const res = await fetch('/api/auth/me');
  return await res.json();
}

async function signup(email, password, name) {
  const res = await fetch('/api/auth/signup', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password, name}),
  });
  return await res.json();
}

async function login(email, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password}),
  });
  return await res.json();
}

async function logout() {
  const res = await fetch('/api/auth/logout', {method: 'POST'});
  return await res.json();
}

async function addToCart(productId) {
  await fetch('/api/cart/add', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({product_id: productId, quantity: 1}),
  });
  await renderCart();
}

async function removeFromCart(productId) {
  await fetch('/api/cart/remove', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({product_id: productId}),
  });
  await renderCart();
}

async function checkout() {
  if (!currentUser) {
    showToast('Please log in to complete checkout.', 'warning');
    showLoginForm();
    return;
  }

  const name = document.getElementById('customer-name') ? document.getElementById('customer-name').value.trim() : currentUser.name;
  const email = document.getElementById('customer-email') ? document.getElementById('customer-email').value.trim() : currentUser.email;
  const address_line = document.getElementById('customer-address') ? document.getElementById('customer-address').value.trim() : '';
  const city = document.getElementById('customer-city') ? document.getElementById('customer-city').value.trim() : '';
  const postal_code = document.getElementById('customer-postal') ? document.getElementById('customer-postal').value.trim() : '';
  const country = document.getElementById('customer-country') ? document.getElementById('customer-country').value.trim() : '';

  // client-side validation: require city and postal code
  if (!city || !postal_code) {
    showToast('Please enter both city and postal code for shipping.', 'warning');
    return;
  }

  const res = await fetch('/api/checkout', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      customer_name: name,
      customer_email: email,
      address_line,
      city,
      postal_code,
      country,
    }),
  });
  
  if (res.ok) {
    const data = await res.json();
    showToast(`Checkout complete! Order ID: ${data.order.id}`, 'success', {variant: 'checkout'});
    const customerNameEl = document.getElementById('customer-name');
    const customerEmailEl = document.getElementById('customer-email');
    if (customerNameEl) customerNameEl.value = '';
    if (customerEmailEl) customerEmailEl.value = '';
    await renderCart();
    await renderProducts(searchInput.value.trim(), categorySelect.value);
    await renderOrders();
  } else {
    const error = await res.json();
    showToast(error.error || 'Checkout failed. Please try again.', 'error');
  }
}

function createProductCard(product) {
  const card = document.createElement('div');
  card.className = 'product-card';
  card.innerHTML = `
    <img src="${product.image}" alt="${product.name}">
    <h3>${product.name}</h3>
    <p class="category-label">${product.category}</p>
    <p>${product.description}</p>
    <p><strong>Le ${product.price.toFixed(2)}</strong></p>
    <p class="inventory-badge">Inventory: ${product.inventory}</p>
    <p class="rating">${product.review_count > 0 ? `Rating: ${product.average_rating} / 5 (${product.review_count} review${product.review_count === 1 ? '' : 's'})` : 'No reviews yet'}</p>
    <div class="product-actions">
      <button onclick="addToCart(${product.id})">Add to cart</button>
      <button class="secondary" onclick="showProductDetails(${product.id})">View details</button>
    </div>
  `;
  return card;
}

function createCartItem(item) {
  const row = document.createElement('div');
  row.className = 'cart-item';
  row.innerHTML = `
    <div class="cart-item-main">
      <span class="cart-item-name">${item.name}</span>
      <div class="cart-quantity-controls">
        <button onclick="changeCartQuantity(${item.id}, -1)">−</button>
        <span>${item.quantity}</span>
        <button onclick="changeCartQuantity(${item.id}, 1)">+</button>
      </div>
    </div>
    <div class="cart-item-meta">
      <span>Le ${item.item_total.toFixed(2)}</span>
      <button class="cart-remove-button" onclick="removeFromCart(${item.id})">Remove</button>
    </div>
  `;
  return row;
}

async function changeCartQuantity(productId, delta) {
  const res = await fetch('/api/cart/add', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({product_id: productId, quantity: delta}),
  });
  const data = await res.json();
  if (!res.ok) {
    showToast(data.error || 'Unable to update quantity.', 'error');
    return;
  }
  await renderCart();
}

function createOrderRow(order) {
  const row = document.createElement('div');
  row.className = 'order-row';
  const itemCount = order.item_count ?? (order.items ? order.items.length : 0);
  const createdAt = order.created_at ? new Date(order.created_at).toLocaleDateString() : '';
  row.innerHTML = `
    <div>
      <strong>${order.id}</strong> — ${order.customer_name}
      <br><small>${itemCount} item(s) • Le ${order.total.toFixed(2)} • ${order.status}</small>
      ${createdAt ? `<br><small>${createdAt}</small>` : ''}
    </div>
    <button onclick="showOrderDetails('${order.id}')">Details</button>
  `;
  return row;
}

async function fetchOrderDetails(orderId) {
  const res = await fetch(`/api/orders/${orderId}`);
  return res.ok ? await res.json() : null;
}

async function fetchPersistenceStatus() {
  const res = await fetch('/api/persistence-status');
  return res.ok ? await res.json() : null;
}

function renderPersistenceStatus(status) {
  if (!persistenceStatus) return;
  if (!status) {
    persistenceStatus.innerHTML = '<p style="color:#c00;">Unable to load persistence status.</p>';
    return;
  }
  persistenceStatus.innerHTML = `
    <p><strong>DB:</strong> ${status.db_file}</p>
    <p><strong>Users:</strong> ${status.users}</p>
    <p><strong>Reviews:</strong> ${status.reviews}</p>
    <p><strong>Orders:</strong> ${status.orders}</p>
    <p><strong>Order items:</strong> ${status.order_items}</p>
  `;
}

function showToast(message, type = 'info', options = {}) {
  if (!toastContainer) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}` + (options.variant ? ` toast-${options.variant}` : '');
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.classList.add('visible'), 10);
  setTimeout(() => {
    toast.classList.remove('visible');
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

async function seedDatabase() {
  if (!seedButton) return;
  seedButton.disabled = true;
  seedButton.textContent = 'Seeding...';
  try {
    const res = await fetch('/api/seed-database', {method: 'POST'});
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Seed request failed.', 'error');
    } else {
      showToast(data.seeded ? 'Sample data seeded successfully.' : 'Sample data already exists.', data.seeded ? 'success' : 'info');
      const status = await fetchPersistenceStatus();
      renderPersistenceStatus(status);
      await renderProducts();
      await renderOrders();
      await renderCart();
    }
  } catch (err) {
    showToast('Unable to seed sample data.', 'error');
  } finally {
    seedButton.disabled = false;
    seedButton.textContent = 'Seed sample data';
  }
}

async function adminSeedDatabase() {
  if (!adminSeedButton || !adminSeedKeyInput) return;
  adminSeedButton.disabled = true;
  adminSeedButton.textContent = 'Admin seeding...';
  const adminKey = adminSeedKeyInput.value.trim();
  try {
    const headers = {'Content-Type': 'application/json'};
    if (adminKey) headers['X-Admin-Key'] = adminKey;
    const res = await fetch('/api/admin/seed-database', {
      method: 'POST',
      headers,
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Admin seed failed.', 'error');
    } else {
      showToast(data.seeded ? 'Admin sample data seeded successfully.' : 'Admin sample data already exists.', data.seeded ? 'success' : 'info');
      const status = await fetchPersistenceStatus();
      renderPersistenceStatus(status);
      await renderProducts();
      await renderOrders();
      await renderCart();
    }
  } catch (err) {
    showToast('Unable to perform admin seed.', 'error');
  } finally {
    adminSeedButton.disabled = false;
    adminSeedButton.textContent = 'Admin seed';
  }
}

async function showOrderDetails(orderId) {
  const order = await fetchOrderDetails(orderId);
  if (!order) {
    alert('Unable to load order details.');
    return;
  }

  const createdAt = order.created_at ? new Date(order.created_at).toLocaleString() : 'N/A';
  const shipping = order.shipping_address || {};
  const shippingAddress = [shipping.address_line, shipping.city, shipping.postal_code, shipping.country]
    .filter(Boolean)
    .join(', ') || 'N/A';

  orderDetailsInfo.innerHTML = `
    <div class="order-summary">
      <div class="order-summary-item"><span class="label">Order</span><span class="value">#${order.id}</span></div>
      <div class="order-summary-item"><span class="label">Customer</span><span class="value">${order.customer_name}</span></div>
      <div class="order-summary-item"><span class="label">Email</span><span class="value">${order.customer_email}</span></div>
      <div class="order-summary-item"><span class="label">Status</span><span class="value status-badge">${order.status}</span></div>
      <div class="order-summary-item"><span class="label">Placed</span><span class="value">${createdAt}</span></div>
      <div class="order-summary-item"><span class="label">Total</span><span class="value">Le ${order.total.toFixed(2)}</span></div>
      <div class="order-summary-item order-shipping"><span class="label">Shipping</span><span class="value">${shippingAddress}</span></div>
    </div>
  `;

  orderDetailsBody.innerHTML = `
    <div class="order-items-table">
      <div class="order-item-row order-item-header">
        <div>Product</div>
        <div>Quantity</div>
        <div>Total</div>
      </div>
      ${order.items.map(item => {
        const product = productCache.find(p => p.id === item.id);
        const thumbnail = product?.image || 'https://via.placeholder.com/80x80?text=Product';
        return `
          <div class="order-item-row">
            <div class="order-item-product">
              <img src="${thumbnail}" alt="${item.name}">
              <div class="order-item-name">
                <strong>${item.name}</strong>
                <span>Le ${item.price.toFixed(2)} each</span>
              </div>
            </div>
            <div class="order-item-qty">x${item.quantity}</div>
            <div class="order-item-total">Le ${item.item_total.toFixed(2)}</div>
          </div>
        `;
      }).join('')}
    </div>
  `;

  orderModal.classList.remove('hidden');
}

function hideOrderDetails() {
  orderModal.classList.add('hidden');
}

async function showProductDetails(productId) {
  selectedProductId = productId;
  const product = productCache.find(p => p.id === productId);
  if (!product) return;
  modalImage.src = product.image;
  modalImage.alt = product.name;
  modalTitle.textContent = product.name;
  modalCategory.textContent = `Category: ${product.category}`;
  modalDescription.textContent = product.description;
  modalPrice.textContent = `Price: Le ${product.price.toFixed(2)}`;
  modalStock.textContent = `In stock: ${product.inventory}`;
  modalRating.textContent = product.review_count > 0 ? `Rating: ${product.average_rating} / 5 (${product.review_count} review${product.review_count === 1 ? '' : 's'})` : 'No reviews yet';
  await renderProductReviews(productId);
  productModal.classList.remove('hidden');
}

function hideProductDetails() {
  productModal.classList.add('hidden');
}

function modalAddToCart() {
  if (!selectedProductId) return;
  addToCart(selectedProductId);
  hideProductDetails();
}

async function renderProducts(search = '', category = '') {
  const products = await fetchProducts(search, category);
  productCache = products;
  productList.innerHTML = '';
  if (products.length === 0) {
    productList.innerHTML = '<p style="grid-column: 1 / -1; color: #666;">No products matched your search.</p>';
    return;
  }
  products.forEach(product => productList.appendChild(createProductCard(product)));
}

async function setupSearch() {
  if (!searchInput) return;
  searchInput.addEventListener('input', async () => {
    const cat = categorySelect ? categorySelect.value : '';
    await renderProducts(searchInput.value.trim(), cat);
  });
  if (categorySelect) {
    categorySelect.addEventListener('change', async () => {
      await renderProducts(searchInput.value.trim(), categorySelect.value);
    });
    // populate categories
    const cats = await fetchCategories();
    cats.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      categorySelect.appendChild(opt);
    });
  }
}

async function renderCart() {
  const cart = await fetchCart();
  cartList.innerHTML = '';
  cart.items.forEach(item => cartList.appendChild(createCartItem(item)));

  const itemCount = cart.items.reduce((sum, item) => sum + item.quantity, 0);
  if (cartBadge) {
    cartBadge.textContent = itemCount > 0 ? `Cart ${itemCount}` : 'Cart empty';
  }

  if (cart.items.length === 0) {
    cartTotal.innerHTML = '<p style="color:#999;"><strong>Total: Le 0.00</strong><br>Cart is empty</p>';
    return;
  }

  if (!currentUser) {
    cartTotal.innerHTML = `
      <p><strong>Total: Le ${cart.total.toFixed(2)}</strong></p>
      <p style="color:#666;">Please log in to checkout.</p>
      <button onclick="showLoginForm()" style="width:100%;background:#0066CC;color:white;padding:8px;border:none;cursor:pointer;border-radius:4px;">Login to checkout</button>
    `;
    return;
  }

  // logged-in user: show checkout button
  cartTotal.innerHTML = `
    <p><strong>Total: Le ${cart.total.toFixed(2)}</strong></p>
    <button onclick="openCheckoutModal()" style="width:100%;background:#1B7C2C;color:white;padding:8px;border:none;cursor:pointer;border-radius:4px;font-weight:bold;">Proceed to checkout</button>
  `;
}

function openCheckoutModal() {
  if (!currentUser) {
    showToast('Please log in first', 'info');
    return;
  }
  document.getElementById('checkout-name').value = currentUser.name || '';
  document.getElementById('checkout-email').value = currentUser.email || '';
  checkoutModal.classList.remove('hidden');
  if (cardElement && cardElement.mount) {
    cardElement.mount('#card-element');
  }
  updateCheckoutSummary();
  updateShippingCost();
  
  // Add event listener for country change
  document.getElementById('checkout-country').addEventListener('change', updateShippingCost);
}

function closeCheckoutModal() {
  checkoutModal.classList.add('hidden');
  if (cardElement && cardElement.unmount) {
    cardElement.unmount();
  }
}

async function updateCheckoutSummary() {
  const cart = await fetchCart();
  const subtotal = cart.total;
  const shipping = currentShippingCost;
  const total = subtotal + shipping;
  
  checkoutSummary.innerHTML = `
    <div class="checkout-summary-line">
      <span>Subtotal:</span>
      <span>$${subtotal.toFixed(2)}</span>
    </div>
    <div class="checkout-summary-line">
      <span>Shipping:</span>
      <span>$${shipping.toFixed(2)}</span>
    </div>
    <div class="checkout-summary-line total">
      <span>Total:</span>
      <span>$${total.toFixed(2)}</span>
    </div>
  `;
}

async function updateShippingCost() {
  const method = document.querySelector('input[name="shipping-method"]:checked').value;
  const country = document.getElementById('checkout-country').value || 'Other';
  
  try {
    const res = await fetch('/api/shipping/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method, country })
    });
    const data = await res.json();
    currentShippingCost = data.shipping_cost;
    shippingCostDisplay.textContent = `Shipping: $${currentShippingCost.toFixed(2)}`;
    updateCheckoutSummary();
  } catch (e) {
    showToast('Error calculating shipping', 'error');
  }
}

async function processCheckout(event) {
  event.preventDefault();
  
  const name = document.getElementById('checkout-name').value.trim();
  const email = document.getElementById('checkout-email').value.trim();
  const address = document.getElementById('checkout-address').value.trim();
  const city = document.getElementById('checkout-city').value.trim();
  const postal = document.getElementById('checkout-postal').value.trim();
  const country = document.getElementById('checkout-country').value.trim();
  
  if (!name || !email || !address || !city || !postal || !country) {
    showToast('Please fill in all fields', 'error');
    return;
  }
  
  try {
    const cart = await fetchCart();
    const cartObj = {};
    cart.items.forEach(item => {
      cartObj[item.product_id] = item.quantity;
    });
    
    // Create payment intent
    const intentRes = await fetch('/api/payment/intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cart: cartObj,
        shipping_cost: currentShippingCost,
        customer_email: email
      })
    });
    
    if (!intentRes.ok) {
      const err = await intentRes.json();
      showToast(`Error: ${err.error}`, 'error');
      return;
    }
    
    const intentData = await intentRes.json();
    
    // Confirm card payment with Stripe
    if (stripe && cardElement) {
      const { error, paymentIntent } = await stripe.confirmCardPayment(
        intentData.client_secret,
        {
          payment_method: {
            card: cardElement,
            billing_details: { name, email }
          }
        }
      );
      
      if (error) {
        cardErrorsDiv.textContent = error.message;
        showToast(`Payment failed: ${error.message}`, 'error');
        return;
      }
      
      if (paymentIntent.status === 'succeeded') {
        // Confirm payment on backend
        const confirmRes = await fetch('/api/payment/confirm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            payment_intent_id: paymentIntent.id,
            customer_name: name,
            customer_email: email,
            address_line: address,
            city,
            postal_code: postal,
            country,
            shipping_cost: currentShippingCost
          })
        });
        
        if (!confirmRes.ok) {
          const err = await confirmRes.json();
          showToast(`Error: ${err.error}`, 'error');
          return;
        }
        
        const order = await confirmRes.json();
        showToast(`Order placed! Order ID: ${order.order_id}`, 'checkout');
        closeCheckoutModal();
        cardErrorsDiv.textContent = '';
        checkoutForm.reset();
        await renderCart();
        await renderOrders();
        await renderProducts();
      }
    }
  } catch (e) {
    showToast('Checkout error', 'error');
  }
}

async function renderOrders() {
  const ordersList = document.getElementById('orders-list');
  if (!ordersList) return;
  
  const orders = await fetchOrders();
  ordersList.innerHTML = '';
  if (orders.length === 0) {
    ordersList.innerHTML = '<p style="color:#999;">No orders yet</p>';
  } else {
    orders.forEach(order => ordersList.appendChild(createOrderRow(order)));
  }
}

function showLoginForm() {
  isSignupMode = false;
  authForm.reset();
  authTitle.textContent = 'Login';
  authNameInput.style.display = 'none';
  authSubmitBtn.textContent = 'Login';
  authToggle.innerHTML = 'Don\'t have an account? <a href="#" onclick="toggleAuthMode(event)" style="color:#0066CC;text-decoration:none;">Sign up</a>';
  authModal.classList.remove('hidden');
}

function toggleAuthMode(event) {
  event.preventDefault();
  isSignupMode = !isSignupMode;
  if (isSignupMode) {
    authTitle.textContent = 'Sign Up';
    authNameInput.style.display = 'block';
    authSubmitBtn.textContent = 'Sign Up';
    authToggle.innerHTML = 'Already have an account? <a href="#" onclick="toggleAuthMode(event)" style="color:#0066CC;text-decoration:none;">Login</a>';
  } else {
    authTitle.textContent = 'Login';
    authNameInput.style.display = 'none';
    authSubmitBtn.textContent = 'Login';
    authToggle.innerHTML = 'Don\'t have an account? <a href="#" onclick="toggleAuthMode(event)" style="color:#0066CC;text-decoration:none;">Sign up</a>';
  }
  authForm.reset();
}

function closeAuthModal() {
  authModal.classList.add('hidden');
  authForm.reset();
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const email = authEmailInput.value.trim();
  const password = authPasswordInput.value.trim();
  const name = authNameInput.value.trim();
  
  try {
    let result;
    if (isSignupMode) {
      result = await signup(email, password, name);
    } else {
      result = await login(email, password);
    }
    
    if (result.success || result.user) {
      currentUser = result.user;
      await updateUserMenu();
      closeAuthModal();
      await renderCart();
      await renderOrders();
      showToast(`Welcome, ${currentUser.name}!`, 'success');
    } else {
      showToast(`Error: ${result.error}`, 'error');
    }
  } catch (e) {
    showToast('Something went wrong. Please try again.', 'error');
  }
}

async function handleLogout() {
  await logout();
  currentUser = null;
  await updateUserMenu();
  await renderCart();
  await renderOrders();
  showToast('Logged out successfully.', 'success');
}

async function updateUserMenu() {
  if (currentUser) {
    userMenu.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;">
        <span style="color:white;">Welcome, ${currentUser.name}!</span>
        <button onclick="handleLogout()" style="background:white;color:#1B7C2C;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-weight:bold;">Logout</button>
      </div>
    `;
  } else {
    userMenu.innerHTML = '<button id="login-btn" onclick="showLoginForm()" style="background:#0066CC;color:white;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;">Login</button>';
  }
}

// Admin Panel Functions
async function getAdminKey() {
  const keyInput = document.getElementById('admin-seed-key');
  return keyInput.value || null;
}

function showAdminPanel() {
  adminModal.classList.remove('hidden');
  adminListProducts();
}

function closeAdminPanel() {
  adminModal.classList.add('hidden');
  adminProductForm.reset();
  document.getElementById('admin-product-id').value = '';
  switchAdminTab('list');
}

function switchAdminTab(tabName) {
  document.querySelectorAll('.admin-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.admin-tab').forEach(tab => tab.classList.add('hidden'));
  
  event.target.classList.add('active');
  document.getElementById(`admin-${tabName}-tab`).classList.remove('hidden');
  
  if (tabName === 'create') {
    document.getElementById('admin-product-submit').textContent = 'Create product';
    document.getElementById('admin-product-id').value = '';
    adminProductForm.reset();
  }
}

async function adminListProducts() {
  try {
    const key = await getAdminKey();
    const headers = key ? { 'X-Admin-Key': key } : {};
    const res = await fetch('/api/admin/products', { headers });
    if (!res.ok) {
      if (res.status === 401) {
        showToast('Admin key required or invalid', 'error');
      } else {
        showToast('Failed to load products', 'error');
      }
      return;
    }
    const products = await res.json();
    renderAdminProductTable(products);
  } catch (e) {
    showToast('Error loading admin products', 'error');
  }
}

function renderAdminProductTable(products) {
  adminProductsBody.innerHTML = '';
  products.forEach(product => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${product.id}</td>
      <td>${product.name}</td>
      <td>$${product.price.toFixed(2)}</td>
      <td>${product.inventory}</td>
      <td>${product.category || 'N/A'}</td>
      <td>
        <button class="admin-btn admin-btn-edit" onclick="adminEditProduct(${product.id})">Edit</button>
        <button class="admin-btn admin-btn-delete" onclick="adminDeleteProduct(${product.id})">Delete</button>
      </td>
    `;
    adminProductsBody.appendChild(row);
  });
}

async function adminEditProduct(productId) {
  try {
    const key = await getAdminKey();
    const headers = key ? { 'X-Admin-Key': key } : {};
    const res = await fetch(`/api/products/${productId}`, { headers });
    if (!res.ok) {
      showToast('Product not found', 'error');
      return;
    }
    const product = await res.json();
    
    document.getElementById('admin-product-id').value = product.id;
    document.getElementById('admin-product-name').value = product.name;
    document.getElementById('admin-product-description').value = product.description;
    document.getElementById('admin-product-price').value = product.price;
    document.getElementById('admin-product-inventory').value = product.inventory;
    document.getElementById('admin-product-category').value = product.category || '';
    document.getElementById('admin-product-image').value = product.image || '';
    
    document.getElementById('admin-product-submit').textContent = 'Update product';
    switchAdminTab('create');
    document.querySelectorAll('.admin-tab-btn')[1].click();
  } catch (e) {
    showToast('Error loading product', 'error');
  }
}

async function adminSaveProduct(event) {
  event.preventDefault();
  const key = await getAdminKey();
  if (!key) {
    showToast('Admin key required', 'error');
    return;
  }
  
  const productId = document.getElementById('admin-product-id').value;
  const productData = {
    name: document.getElementById('admin-product-name').value,
    description: document.getElementById('admin-product-description').value,
    price: parseFloat(document.getElementById('admin-product-price').value),
    inventory: parseInt(document.getElementById('admin-product-inventory').value),
    category: document.getElementById('admin-product-category').value,
    image: document.getElementById('admin-product-image').value,
  };
  
  try {
    const method = productId ? 'PUT' : 'POST';
    const url = productId ? `/api/admin/products/${productId}` : '/api/admin/products';
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': key,
      },
      body: JSON.stringify(productData),
    });
    
    if (!res.ok) {
      const errorData = await res.json();
      showToast(`Error: ${errorData.error || 'Failed to save product'}`, 'error');
      return;
    }
    
    const action = productId ? 'updated' : 'created';
    showToast(`Product ${action} successfully`, 'success');
    adminProductForm.reset();
    document.getElementById('admin-product-id').value = '';
    switchAdminTab('list');
    adminListProducts();
  } catch (e) {
    showToast('Error saving product', 'error');
  }
}

async function adminDeleteProduct(productId) {
  if (!confirm('Are you sure you want to delete this product?')) return;
  
  try {
    const key = await getAdminKey();
    if (!key) {
      showToast('Admin key required', 'error');
      return;
    }
    
    const res = await fetch(`/api/admin/products/${productId}`, {
      method: 'DELETE',
      headers: {
        'X-Admin-Key': key,
      },
    });
    
    if (!res.ok) {
      const errorData = await res.json();
      showToast(`Error: ${errorData.error || 'Failed to delete product'}`, 'error');
      return;
    }
    
    showToast('Product deleted successfully', 'success');
    adminListProducts();
    await renderProducts();
  } catch (e) {
    showToast('Error deleting product', 'error');
  }
}

// Analytics Dashboard Functions
function showAnalyticsDashboard() {
  analyticsModal.classList.remove('hidden');
  loadAnalyticsData();
}

function closeAnalyticsDashboard() {
  analyticsModal.classList.add('hidden');
}

function switchAnalyticsTab(tabName) {
  document.querySelectorAll('.analytics-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.analytics-tab').forEach(tab => tab.classList.add('hidden'));
  
  event.target.classList.add('active');
  document.getElementById(`${tabName}-tab`).classList.remove('hidden');
  
  if (tabName === 'revenue') {
    setTimeout(() => initDailyRevenueChart(), 100);
  }
}

async function loadAnalyticsData() {
  try {
    const [overview, products, customers, revenue] = await Promise.all([
      fetch('/api/analytics/overview').then(r => r.json()),
      fetch('/api/analytics/products').then(r => r.json()),
      fetch('/api/analytics/customers').then(r => r.json()),
      fetch('/api/analytics/revenue').then(r => r.json())
    ]);
    
    renderOverviewMetrics(overview);
    renderProductsTable(products);
    renderCustomersMetrics(customers);
    renderRevenueMetrics(revenue);
  } catch (e) {
    showToast('Error loading analytics', 'error');
  }
}

function renderOverviewMetrics(data) {
  document.getElementById('metric-orders').textContent = data.total_orders;
  document.getElementById('metric-revenue').textContent = `$${data.total_revenue.toFixed(2)}`;
  document.getElementById('metric-avg-order').textContent = `$${data.avg_order_value.toFixed(2)}`;
  document.getElementById('metric-customers').textContent = data.total_customers;
  
  initRevenueChart(data.revenue_trend);
}

function renderProductsTable(products) {
  const tbody = document.getElementById('products-table-body');
  tbody.innerHTML = '';
  products.forEach(p => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${p.name}</td>
      <td>${p.units_sold}</td>
      <td>$${p.revenue.toFixed(2)}</td>
      <td>${p.inventory}</td>
    `;
    tbody.appendChild(row);
  });
}

function renderCustomersMetrics(data) {
  document.getElementById('cust-total').textContent = data.total_customers;
  document.getElementById('cust-repeat').textContent = data.repeat_customers;
  document.getElementById('cust-repeat-rate').textContent = `${data.repeat_rate.toFixed(1)}%`;
  document.getElementById('cust-avg-orders').textContent = data.avg_orders_per_customer.toFixed(2);
  
  const tbody = document.getElementById('customers-table-body');
  tbody.innerHTML = '';
  data.top_customers.forEach(c => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${c.name}</td>
      <td>${c.email}</td>
      <td>${c.order_count}</td>
      <td>$${c.total_spent.toFixed(2)}</td>
    `;
    tbody.appendChild(row);
  });
}

function renderRevenueMetrics(data) {
  document.getElementById('rev-total').textContent = `$${data.total_revenue.toFixed(2)}`;
  document.getElementById('rev-orders').textContent = data.total_orders;
  document.getElementById('rev-aov').textContent = `$${data.avg_order_value.toFixed(2)}`;
  document.getElementById('rev-avg-items').textContent = data.avg_items_per_order.toFixed(2);
  
  // Store for later chart rendering
  window.revenueData = data.daily_revenue;
}

function initRevenueChart(data) {
  const ctx = document.getElementById('revenue-chart');
  if (!ctx) return;
  
  if (revenueChart) revenueChart.destroy();
  
  revenueChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.day),
      datasets: [{
        label: 'Revenue',
        data: data.map(d => d.revenue),
        borderColor: '#1B7C2C',
        backgroundColor: 'rgba(27, 124, 44, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#1B7C2C'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: val => '$' + val.toFixed(0) }
        }
      }
    }
  });
}

function initDailyRevenueChart() {
  const ctx = document.getElementById('daily-revenue-chart');
  if (!ctx || !window.revenueData) return;
  
  if (dailyRevenueChart) dailyRevenueChart.destroy();
  
  dailyRevenueChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: window.revenueData.map(d => d.day),
      datasets: [{
        label: 'Daily Revenue',
        data: window.revenueData.map(d => d.revenue),
        backgroundColor: '#1B7C2C',
        borderColor: '#0066CC',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: val => '$' + val.toFixed(0) }
        }
      }
    }
  });
}

window.addEventListener('DOMContentLoaded', async () => {
  await initializeStripe();
  currentUser = await getCurrentUser();
  await updateUserMenu();
  await setupSearch();
  await renderProducts();
  await renderCart();
  await renderOrders();
  const status = await fetchPersistenceStatus();
  renderPersistenceStatus(status);
});
