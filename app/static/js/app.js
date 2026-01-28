/**
 * Product Intelligence Scraper - Frontend Application
 */

// Global state
const state = {
    products: [],
    query: '',
    sources: [],
    sortColumn: null,
    sortDirection: 'asc'
};

// DOM Elements
const elements = {
    searchForm: document.getElementById('searchForm'),
    searchInput: document.getElementById('searchInput'),
    searchBtn: document.getElementById('searchBtn'),
    sourceCheckboxes: document.getElementById('sourceCheckboxes'),
    maxResults: document.getElementById('maxResults'),
    resultsSection: document.getElementById('resultsSection'),
    resultsStats: document.getElementById('resultsStats'),
    resultsBody: document.getElementById('resultsBody'),
    errorsContainer: document.getElementById('errorsContainer'),
    errorsList: document.getElementById('errorsList'),
    emptyState: document.getElementById('emptyState'),
    noResults: document.getElementById('noResults'),
    loadingState: document.getElementById('loadingState'),
    loadingDetail: document.getElementById('loadingDetail'),
    errorState: document.getElementById('errorState'),
    errorMessage: document.getElementById('errorMessage'),
    exportJsonBtn: document.getElementById('exportJsonBtn'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
    productModal: document.getElementById('productModal'),
    modalClose: document.getElementById('modalClose'),
    modalBody: document.getElementById('modalBody')
};

// API endpoints
const API = {
    sources: '/api/products/sources',
    search: '/api/products/search',
    exportJson: '/api/products/export/json',
    exportCsv: '/api/products/export/csv'
};

/**
 * Initialize the application
 */
async function init() {
    await loadSources();
    setupEventListeners();
}

/**
 * Load available sources from API
 */
async function loadSources() {
    try {
        const response = await fetch(API.sources);
        const data = await response.json();

        state.sources = data.sources;
        renderSourceCheckboxes(data.sources);
    } catch (error) {
        console.error('Failed to load sources:', error);
        // Use default sources
        const defaultSources = ['amazon', 'ebay', 'bestbuy', 'walmart'];
        renderSourceCheckboxes(defaultSources);
    }
}

/**
 * Render source checkboxes
 */
function renderSourceCheckboxes(sources) {
    elements.sourceCheckboxes.innerHTML = sources.map(source => `
        <label>
            <input type="checkbox" name="source" value="${source}" checked>
            ${capitalizeFirst(source)}
        </label>
    `).join('');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Search form submission
    elements.searchForm.addEventListener('submit', handleSearch);

    // Export buttons
    elements.exportJsonBtn.addEventListener('click', () => exportResults('json'));
    elements.exportCsvBtn.addEventListener('click', () => exportResults('csv'));

    // Modal close
    elements.modalClose.addEventListener('click', closeModal);
    elements.productModal.addEventListener('click', (e) => {
        if (e.target === elements.productModal) closeModal();
    });

    // Keyboard events
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    // Table sorting
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => handleSort(th.dataset.sort));
    });
}

/**
 * Handle search form submission
 */
async function handleSearch(e) {
    e.preventDefault();

    const query = elements.searchInput.value.trim();
    if (!query) return;

    state.query = query;

    // Get selected sources
    const checkedSources = Array.from(
        document.querySelectorAll('input[name="source"]:checked')
    ).map(cb => cb.value);

    const maxResults = parseInt(elements.maxResults.value);

    // Show loading state
    showState('loading');
    setLoadingState(true);

    try {
        const response = await fetch(API.search, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                sources: checkedSources.length > 0 ? checkedSources : null,
                max_results: maxResults
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        state.products = data.products;
        state.sortColumn = null;
        state.sortDirection = 'asc';

        if (data.products.length === 0) {
            showState('noResults');
        } else {
            renderResults(data);
            showState('results');
        }

        // Show errors if any
        if (Object.keys(data.errors).length > 0) {
            showErrors(data.errors);
        }

    } catch (error) {
        console.error('Search failed:', error);
        elements.errorMessage.textContent = error.message || 'Unable to complete the search. Please try again.';
        showState('error');
    } finally {
        setLoadingState(false);
    }
}

/**
 * Render search results
 */
function renderResults(data) {
    // Update stats
    elements.resultsStats.textContent =
        `Found ${data.total_results} products from ${data.sources_searched.length} sources in ${data.search_time_seconds.toFixed(2)}s`;

    // Render table
    renderProductTable(data.products);
}

/**
 * Render product table
 */
function renderProductTable(products) {
    elements.resultsBody.innerHTML = products.map((product, index) => `
        <tr data-index="${index}">
            <td class="col-image">
                ${product.image_url
                    ? `<img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.title)}" class="product-image" onerror="this.outerHTML='<div class=\\'product-image-placeholder\\'>No Image</div>'">`
                    : '<div class="product-image-placeholder">No Image</div>'
                }
            </td>
            <td class="col-product">
                <div class="product-title">${escapeHtml(product.title)}</div>
                ${product.brand ? `<div class="product-brand">${escapeHtml(product.brand)}</div>` : ''}
            </td>
            <td class="col-source">
                <span class="source-badge source-${product.source}">${capitalizeFirst(product.source)}</span>
            </td>
            <td class="col-price">
                ${product.price !== null
                    ? `<div class="price-current">${formatCurrency(product.price, product.currency)}</div>
                       ${product.original_price ? `<div class="price-original">${formatCurrency(product.original_price, product.currency)}</div>` : ''}`
                    : '<span class="text-secondary">N/A</span>'
                }
            </td>
            <td class="col-discount">
                ${product.discount_percent
                    ? `<span class="discount-badge">-${product.discount_percent}%</span>`
                    : '-'
                }
            </td>
            <td class="col-rating">
                ${product.rating !== null
                    ? `<div class="rating-stars">${renderStars(product.rating)}<span class="rating-value">${product.rating}</span></div>
                       ${product.rating_count ? `<div class="rating-count">(${formatNumber(product.rating_count)})</div>` : ''}`
                    : '-'
                }
            </td>
            <td class="col-availability">
                <span class="availability-badge availability-${product.availability}">
                    ${formatAvailability(product.availability)}
                </span>
            </td>
            <td class="col-actions">
                <a href="${escapeHtml(product.url)}" target="_blank" rel="noopener" class="action-btn">View</a>
            </td>
        </tr>
    `).join('');

    // Add click handlers for detail view
    elements.resultsBody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('dblclick', () => {
            const index = parseInt(row.dataset.index);
            showProductDetail(state.products[index]);
        });
    });
}

/**
 * Handle table sorting
 */
function handleSort(column) {
    // Toggle direction if same column
    if (state.sortColumn === column) {
        state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        state.sortColumn = column;
        state.sortDirection = 'asc';
    }

    // Sort products
    const sorted = [...state.products].sort((a, b) => {
        let aVal = getSortValue(a, column);
        let bVal = getSortValue(b, column);

        if (aVal === null) return 1;
        if (bVal === null) return -1;

        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }

        if (aVal < bVal) return state.sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return state.sortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    // Update table
    renderProductTable(sorted);

    // Update header styles
    document.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.dataset.sort === column) {
            th.classList.add(`sort-${state.sortDirection}`);
        }
    });
}

/**
 * Get sort value for a product
 */
function getSortValue(product, column) {
    switch (column) {
        case 'title': return product.title;
        case 'source': return product.source;
        case 'price': return product.price;
        case 'discount': return product.discount_percent;
        case 'rating': return product.rating;
        case 'availability': return product.availability;
        default: return null;
    }
}

/**
 * Export results
 */
async function exportResults(format) {
    if (!state.query) return;

    const checkedSources = Array.from(
        document.querySelectorAll('input[name="source"]:checked')
    ).map(cb => cb.value);

    const params = new URLSearchParams({
        q: state.query,
        max_results: elements.maxResults.value
    });

    if (checkedSources.length > 0) {
        params.append('sources', checkedSources.join(','));
    }

    const url = format === 'json'
        ? `${API.exportJson}?${params}`
        : `${API.exportCsv}?${params}`;

    // Trigger download
    window.location.href = url;
}

/**
 * Show product detail modal
 */
function showProductDetail(product) {
    const specsHtml = Object.keys(product.specifications).length > 0
        ? `<div class="modal-specs">
            <h4>Specifications</h4>
            <table class="specs-table">
                ${Object.entries(product.specifications).map(([key, value]) =>
                    `<tr><td>${escapeHtml(key)}</td><td>${escapeHtml(value)}</td></tr>`
                ).join('')}
            </table>
           </div>`
        : '';

    elements.modalBody.innerHTML = `
        <div class="modal-product-header">
            ${product.image_url
                ? `<img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.title)}" class="modal-product-image">`
                : '<div class="modal-product-image" style="background: var(--border-color); display: flex; align-items: center; justify-content: center;">No Image</div>'
            }
            <div class="modal-product-info">
                <h3 class="modal-product-title">${escapeHtml(product.title)}</h3>
                ${product.brand ? `<p style="color: var(--text-secondary); margin-bottom: 12px;">by ${escapeHtml(product.brand)}</p>` : ''}
                ${product.price !== null
                    ? `<div class="modal-product-price">${formatCurrency(product.price, product.currency)}</div>`
                    : ''
                }
                ${product.original_price
                    ? `<p style="text-decoration: line-through; color: var(--text-secondary);">Was ${formatCurrency(product.original_price, product.currency)}</p>`
                    : ''
                }
                ${product.discount_percent
                    ? `<span class="discount-badge" style="margin: 8px 0; display: inline-block;">Save ${product.discount_percent}%</span>`
                    : ''
                }
                <p style="margin: 12px 0;">
                    <span class="availability-badge availability-${product.availability}">
                        ${formatAvailability(product.availability)}
                    </span>
                </p>
                ${product.rating !== null
                    ? `<p style="margin-top: 12px;">${renderStars(product.rating)} ${product.rating}/5 ${product.rating_count ? `(${formatNumber(product.rating_count)} reviews)` : ''}</p>`
                    : ''
                }
                <p style="margin-top: 16px;">
                    <a href="${escapeHtml(product.url)}" target="_blank" rel="noopener" class="btn btn-primary">
                        View on ${capitalizeFirst(product.source)}
                    </a>
                </p>
            </div>
        </div>
        ${specsHtml}
    `;

    elements.productModal.classList.add('active');
}

/**
 * Close modal
 */
function closeModal() {
    elements.productModal.classList.remove('active');
}

/**
 * Show errors
 */
function showErrors(errors) {
    elements.errorsList.innerHTML = Object.entries(errors)
        .map(([source, message]) => `<li><strong>${capitalizeFirst(source)}:</strong> ${escapeHtml(message)}</li>`)
        .join('');
    elements.errorsContainer.style.display = 'block';
}

/**
 * Show a specific state
 */
function showState(stateName) {
    // Hide all states
    elements.resultsSection.style.display = 'none';
    elements.emptyState.style.display = 'none';
    elements.noResults.style.display = 'none';
    elements.loadingState.style.display = 'none';
    elements.errorState.style.display = 'none';
    elements.errorsContainer.style.display = 'none';

    // Show requested state
    switch (stateName) {
        case 'empty':
            elements.emptyState.style.display = 'block';
            break;
        case 'loading':
            elements.loadingState.style.display = 'block';
            break;
        case 'results':
            elements.resultsSection.style.display = 'block';
            break;
        case 'noResults':
            elements.noResults.style.display = 'block';
            break;
        case 'error':
            elements.errorState.style.display = 'block';
            break;
    }
}

/**
 * Set loading state for search button
 */
function setLoadingState(loading) {
    const btnText = elements.searchBtn.querySelector('.btn-text');
    const btnLoading = elements.searchBtn.querySelector('.btn-loading');

    if (loading) {
        btnText.style.display = 'none';
        btnLoading.style.display = 'inline-flex';
        elements.searchBtn.disabled = true;
        elements.searchInput.disabled = true;
    } else {
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
        elements.searchBtn.disabled = false;
        elements.searchInput.disabled = false;
    }
}

// Utility Functions

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function renderStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalf = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalf ? 1 : 0);

    return '★'.repeat(fullStars) +
           (hasHalf ? '½' : '') +
           '☆'.repeat(emptyStars);
}

function formatAvailability(status) {
    const labels = {
        'in_stock': 'In Stock',
        'out_of_stock': 'Out of Stock',
        'limited': 'Limited',
        'pre_order': 'Pre-Order',
        'unknown': 'Unknown'
    };
    return labels[status] || status;
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', init);
