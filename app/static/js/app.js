/**
 * Product Intelligence Scraper - Frontend Application
 */

// Global state
const state = {
    products: [],
    query: '',
    sources: [],
    groupedProducts: {},
    activeSources: []
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

// Source display names mapping
const SOURCE_NAMES = {
    'amazon': 'Amazon',
    'ebay': 'eBay',
    'bestbuy': 'Best Buy',
    'walmart': 'Walmart',
    'flipkart': 'Flipkart',
    'snapdeal': 'Snapdeal',
    'reliancedigital': 'Reliance Digital',
    'croma': 'Croma',
    'tatacliq': 'Tata Cliq'
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
        const defaultSources = ['amazon', 'ebay', 'bestbuy', 'flipkart', 'snapdeal', 'reliancedigital', 'croma', 'tatacliq'];
        state.sources = defaultSources;
        renderSourceCheckboxes(defaultSources);
    }
}

/**
 * Render source checkboxes
 */
function renderSourceCheckboxes(sources) {
    const indianSources = ['flipkart', 'snapdeal', 'reliancedigital', 'croma', 'tatacliq'];
    
    const grouped = {
        'International Sites': [],
        'Indian Sites': []
    };

    sources.forEach(source => {
        if (indianSources.includes(source)) {
            grouped['Indian Sites'].push(source);
        } else {
            grouped['International Sites'].push(source);
        }
    });

    let html = '';

    for (const [category, categorySources] of Object.entries(grouped)) {
        if (categorySources.length > 0) {
            html += `<div class="source-category"><span class="category-label">${category}</span>`;
            html += categorySources.map(source => `
                <label class="source-label">
                    <input type="checkbox" name="source" value="${source}" checked>
                    <span class="source-name">${SOURCE_NAMES[source] || capitalizeFirst(source)}</span>
                </label>
            `).join('');
            html += `</div>`;
        }
    }

    elements.sourceCheckboxes.innerHTML = html;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    elements.searchForm.addEventListener('submit', handleSearch);
    elements.exportJsonBtn.addEventListener('click', () => exportResults('json'));
    elements.exportCsvBtn.addEventListener('click', () => exportResults('csv'));
    elements.modalClose.addEventListener('click', closeModal);
    elements.productModal.addEventListener('click', (e) => {
        if (e.target === elements.productModal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

/**
 * Normalize product title for grouping
 */
function normalizeTitle(title) {
    // Remove common variations to group similar products
    return title
        .toLowerCase()
        .replace(/\d+\s*(pro|plus|max|lite|se|ultra|5g|lte|2nd gen|3rd gen|4th gen)/gi, '')
        .replace(/[™®©]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Extract base product name
 */
function getBaseProductName(title) {
    // Extract the main product name (e.g., "Samsung Galaxy S24 Ultra")
    const parts = title.split(' - ');
    return parts[0].trim();
}

/**
 * Group products by normalized title
 */
function groupProductsByName(products) {
    const grouped = {};
    
    products.forEach(product => {
        const baseName = getBaseProductName(product.title);
        const normalized = normalizeTitle(baseName);
        
        if (!grouped[normalized]) {
            grouped[normalized] = {
                name: baseName,
                image: product.image_url,
                brand: product.brand,
                sources: {}
            };
        }
        
        grouped[normalized].sources[product.source] = {
            price: product.price,
            originalPrice: product.original_price,
            currency: product.currency,
            discount: product.discount_percent,
            url: product.url,
            availability: product.availability,
            rating: product.rating
        };
    });
    
    return Object.values(grouped);
}

/**
 * Handle search form submission
 */
async function handleSearch(e) {
    e.preventDefault();

    const query = elements.searchInput.value.trim();
    if (!query) return;

    state.query = query;

    const checkedSources = Array.from(
        document.querySelectorAll('input[name="source"]:checked')
    ).map(cb => cb.value);
    
    state.activeSources = checkedSources;

    const maxResults = parseInt(elements.maxResults.value);

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

        // Group products by name
        state.groupedProducts = groupProductsByName(data.products);
        state.products = data.products;

        if (state.groupedProducts.length === 0) {
            showState('noResults');
        } else {
            renderResults(data);
            showState('results');
        }

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
 * Render search results - Comparison Table
 */
function renderResults(data) {
    const sourcesCount = new Set();
    Object.values(state.groupedProducts).forEach(p => {
        Object.keys(p.sources).forEach(s => sourcesCount.add(s));
    });
    
    elements.resultsStats.textContent =
        `Found ${state.groupedProducts.length} unique products from ${sourcesCount.size} sites in ${data.search_time_seconds.toFixed(2)}s`;

    renderComparisonTable();
}

/**
 * Render comparison table with one row per product
 */
function renderComparisonTable() {
    const sources = state.activeSources;
    
    let html = `
        <table class="comparison-table">
            <thead>
                <tr>
                    <th class="col-product">Product</th>
                    <th class="col-image-header">Image</th>
                    ${sources.map(source => `
                        <th class="col-price source-${source}">${SOURCE_NAMES[source] || capitalizeFirst(source)}</th>
                    `).join('')}
                </tr>
            </thead>
            <tbody>
    `;

    state.groupedProducts.forEach((product, index) => {
        html += `
            <tr data-index="${index}">
                <td class="col-product">
                    <div class="product-name">${escapeHtml(product.name)}</div>
                    ${product.brand ? `<div class="product-brand">${escapeHtml(product.brand)}</div>` : ''}
                </td>
                <td class="col-image">
                    ${product.image 
                        ? `<img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name)}" class="product-image" onerror="this.style.display='none'">`
                        : '<div class="image-placeholder">No Image</div>'
                    }
                </td>
                ${sources.map(source => {
                    const sourceData = product.sources[source];
                    if (!sourceData) {
                        return `<td class="col-price source-${source}"><span class="not-available">Not Available</span></td>`;
                    }
                    return `
                        <td class="col-price source-${source}">
                            <div class="price-link-cell">
                                ${sourceData.price !== null 
                                    ? `<div class="price-value">${formatCurrency(sourceData.price, sourceData.currency)}</div>`
                                    : '<span class="price-na">N/A</span>'
                                }
                                ${sourceData.originalPrice 
                                    ? `<div class="original-price">${formatCurrency(sourceData.originalPrice, sourceData.currency)}</div>`
                                    : ''
                                }
                                ${sourceData.discount 
                                    ? `<div class="discount-badge">-${sourceData.discount}%</div>`
                                    : ''
                                }
                                <a href="${escapeHtml(sourceData.url)}" target="_blank" rel="noopener" class="view-link">
                                    View
                                </a>
                            </div>
                        </td>
                    `;
                }).join('')}
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    elements.resultsBody.innerHTML = html;
}

/**
 * Handle table sorting
 */
function handleSort(column) {
    // Sort grouped products
    const sorted = [...state.groupedProducts].sort((a, b) => {
        // Get lowest price from any source for comparison
        const getLowestPrice = (p) => {
            const prices = Object.values(p.sources)
                .map(s => s.price)
                .filter(p => p !== null);
            return prices.length > 0 ? Math.min(...prices) : null;
        };

        let aVal, bVal;

        if (column === 'price') {
            aVal = getLowestPrice(a);
            bVal = getLowestPrice(b);
            if (aVal === null) return 1;
            if (bVal === null) return -1;
        } else if (column === 'name') {
            aVal = a.name.toLowerCase();
            bVal = b.name.toLowerCase();
        } else {
            return 0;
        }

        if (aVal < bVal) return 1;
        if (aVal > bVal) return -1;
        return 0;
    });

    state.groupedProducts = sorted;
    renderComparisonTable();
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

    window.location.href = url;
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
        .map(([source, message]) => `<li><strong>${SOURCE_NAMES[source] || capitalizeFirst(source)}:</strong> ${escapeHtml(message)}</li>`)
        .join('');
    elements.errorsContainer.style.display = 'block';
}

/**
 * Show a specific state
 */
function showState(stateName) {
    elements.resultsSection.style.display = 'none';
    elements.emptyState.style.display = 'none';
    elements.noResults.style.display = 'none';
    elements.loadingState.style.display = 'none';
    elements.errorState.style.display = 'none';
    elements.errorsContainer.style.display = 'none';

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

function formatCurrency(amount, currency = 'INR') {
    if (currency === 'INR') {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        }).format(amount);
    }
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

function formatAvailability(status) {
    const labels = {
        'in_stock': 'In Stock',
        'out_of_stock': 'Out of Stock',
        'limited': 'Limited',
        'pre_order': 'Pre-Order',
        'unknown': 'Unknown'
    };
    return labels[status] || 'Unknown';
}

// Initialize the app
init();
