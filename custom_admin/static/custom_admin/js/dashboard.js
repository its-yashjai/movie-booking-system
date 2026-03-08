/**
 * Custom Admin Dashboard Application
 * 
 * This class manages all dashboard functionality including:
 * - Fetching real-time statistics from API endpoints
 * - Rendering interactive charts using Chart.js
 * - Populating data tables with booking information
 * - Error handling and user feedback
 * 
 * Architecture:
 * - API calls are made to /custom-admin/api/* endpoints
 * - All data is fetched asynchronously to prevent page blocking
 * - Charts are re-rendered when data updates
 * - HTML elements are populated using DOM manipulation
 */
class AdminDashboard {
    /**
     * Initialize dashboard with API base URL and setup
     */
    constructor() {
        // Store Chart.js instances for cleanup/refresh
        this.charts = {};
        // Base URL for all API endpoints
        this.apiBaseUrl = '/custom-admin/api';
        // Flag to prevent multiple simultaneous requests
        this.isLoading = false;
        // Initialize dashboard on page load
        this.init();
    }

    /**
     * Show error message to user
     * @param {string} message - Error message to display
     */
    showError(message) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'error-message';
        errorContainer.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <span>${this.escapeHtml(message)}</span>
        `;
        
        const mainContainer = document.querySelector('.container-main');
        if (mainContainer) {
            mainContainer.insertBefore(errorContainer, mainContainer.firstChild);
            
            setTimeout(() => {
                errorContainer.style.opacity = '0';
                errorContainer.style.transition = 'opacity 0.3s ease';
                setTimeout(() => errorContainer.remove(), 300);
            }, 5000);
        }
    }

    /**
     * Initialize dashboard by loading all data
     * 
     * Called automatically on page load via DOMContentLoaded event.
     * Loads stats, revenue data, bookings, and theaters in parallel.
     */
    async init() {
        if (this.isLoading) return;
        this.isLoading = true;
        
        try {
            console.log('Initializing dashboard...');
            // Load all data concurrently
            await Promise.all([
                this.loadStats(),
                this.loadRevenue(),
                this.loadBookings()
            ]);
            
            console.log('Dashboard data loaded successfully');
            // Setup filter event listeners
            this.setupFilterListeners();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError('Failed to load dashboard data. Please refresh the page.');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Setup event listeners for filter controls
     */
    setupFilterListeners() {
        const movieFilter = document.getElementById('movieFilter');
        const periodFilter = document.getElementById('periodFilter');
        const theaterFilter = document.getElementById('theaterFilter');
        const dateRangeGroup = document.getElementById('dateRangeGroup');
        const dateFrom = document.getElementById('dateFrom');
        const dateTo = document.getElementById('dateTo');
        const applyBtn = document.getElementById('applyFilters');
        const resetBtn = document.getElementById('resetFilters');

        if (!applyBtn || !resetBtn) return;

        // Load filter options
        this.loadFilterOptions();

        // Show/hide date range when custom period is selected
        if (periodFilter && dateRangeGroup) {
            periodFilter.addEventListener('change', (e) => {
                if (e.target.value === 'custom') {
                    dateRangeGroup.style.display = 'block';
                    // Set default dates
                    if (!dateFrom.value) {
                        const today = new Date();
                        const lastMonth = new Date(today);
                        lastMonth.setMonth(lastMonth.getMonth() - 1);
                        dateFrom.value = lastMonth.toISOString().split('T')[0];
                        dateTo.value = today.toISOString().split('T')[0];
                    }
                } else {
                    dateRangeGroup.style.display = 'none';
                }
                this.updateActiveFilterCount();
            });
        }

        // Update filter count on any filter change
        [movieFilter, periodFilter, theaterFilter, dateFrom, dateTo].forEach(el => {
            if (el) {
                el.addEventListener('change', () => this.updateActiveFilterCount());
            }
        });

        applyBtn.addEventListener('click', () => {
            this.applyFilters();
        });

        resetBtn.addEventListener('click', () => {
            // Reset all filter values
            if (movieFilter) movieFilter.value = '';
            if (periodFilter) periodFilter.value = 'all';
            if (theaterFilter) theaterFilter.value = '';
            if (dateFrom) dateFrom.value = '';
            if (dateTo) dateTo.value = '';
            if (dateRangeGroup) dateRangeGroup.style.display = 'none';
            
            this.updateActiveFilterCount();
            
            // Reload dashboard data
            this.init();
        });

        // Initial filter count update
        this.updateActiveFilterCount();
    }

    /**
     * Update active filter count badge
     */
    updateActiveFilterCount() {
        const movieFilter = document.getElementById('movieFilter')?.value;
        const periodFilter = document.getElementById('periodFilter')?.value;
        const theaterFilter = document.getElementById('theaterFilter')?.value;
        const dateFrom = document.getElementById('dateFrom')?.value;
        const dateTo = document.getElementById('dateTo')?.value;
        const badge = document.getElementById('activeFiltersCount');
        
        let count = 0;
        if (movieFilter) count++;
        if (theaterFilter) count++;
        if (periodFilter && periodFilter !== 'all') count++;
        if (dateFrom || dateTo) count++;
        
        if (badge) {
            if (count > 0) {
                badge.textContent = `${count} active`;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    /**
     * Load available filter options (movies and theaters)
     */
    async loadFilterOptions() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/filter-options/`, {
                credentials: 'include'
            });
            if (!response.ok) {
                throw new Error(`Filter options API error: ${response.status}`);
            }

            const data = await response.json();
            
            // Populate movie filter
            const movieFilter = document.getElementById('movieFilter');
            if (movieFilter && Array.isArray(data.movies)) {
                data.movies.forEach(movie => {
                    const option = document.createElement('option');
                    option.value = movie.id;
                    option.textContent = movie.title;
                    movieFilter.appendChild(option);
                });
            }

            // Populate theater filter
            const theaterFilter = document.getElementById('theaterFilter');
            if (theaterFilter && Array.isArray(data.theaters)) {
                data.theaters.forEach(theater => {
                    const option = document.createElement('option');
                    option.value = theater.id;
                    option.textContent = theater.name;
                    theaterFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    }

    /**
     * Apply selected filters and reload data
     */
    async applyFilters() {
        const movieFilter = document.getElementById('movieFilter')?.value;
        const periodFilter = document.getElementById('periodFilter')?.value;
        const theaterFilter = document.getElementById('theaterFilter')?.value;

        // Build query string
        const params = new URLSearchParams();
        if (movieFilter) params.append('movie_id', movieFilter);
        if (periodFilter && periodFilter !== 'all') params.append('period', periodFilter);
        if (theaterFilter) params.append('theater_id', theaterFilter);

        // Store filter state
        this.currentFilters = {
            movie_id: movieFilter,
            period: periodFilter,
            theater_id: theaterFilter
        };

        // Reload data with new filters
        if (this.isLoading) return;
        this.isLoading = true;
        
        try {
            await Promise.all([
                this.loadStats(),
                this.loadRevenue(),
                this.loadBookings()
            ]);
        } catch (error) {
            console.error('Error applying filters:', error);
            this.showError('Failed to apply filters. Please try again.');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Build query parameters from current filter state
     */
    buildFilterParams() {
        const params = new URLSearchParams();
        
        const movieFilter = document.getElementById('movieFilter')?.value;
        const periodFilter = document.getElementById('periodFilter')?.value;
        const theaterFilter = document.getElementById('theaterFilter')?.value;
        const dateFrom = document.getElementById('dateFrom')?.value;
        const dateTo = document.getElementById('dateTo')?.value;
        
        if (movieFilter) params.append('movie_id', movieFilter);
        if (theaterFilter) params.append('theater_id', theaterFilter);
        
        // Handle period filter
        if (periodFilter === 'custom') {
            // Use custom date range
            if (dateFrom) params.append('date_from', dateFrom);
            if (dateTo) params.append('date_to', dateTo);
        } else if (periodFilter && periodFilter !== 'all') {
            // Use predefined period
            params.append('period', periodFilter);
        }
        
        return params.toString();
    }

    /**
     * Load and display summary statistics
     * 
     * Fetches: Total revenue, today's revenue, total bookings, today's bookings
     * Updates stat cards with formatted currency and numbers
     * 
     * API: GET /custom-admin/api/stats/
     * Returns: {total_revenue, today_revenue, total_bookings, today_bookings}
     */
    async loadStats() {
        try {
            console.log('[loadStats] Starting...');
            const params = this.buildFilterParams();
            console.log('[loadStats] Filter params:', params);
            const response = await fetch(`${this.apiBaseUrl}/stats/?${params}`, {
                credentials: 'include'
            });
            console.log('[loadStats] Response status:', response.status);
            if (!response.ok) {
                throw new Error(`Stats API error: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Stats data:', data);
            
            // Validate data
            if (typeof data.total_revenue !== 'number' || 
                typeof data.today_revenue !== 'number' ||
                typeof data.total_bookings !== 'number' ||
                typeof data.today_bookings !== 'number') {
                throw new Error('Invalid stats data format');
            }
            
            // Update total revenue card with formatted currency
            const totalRevenueEl = document.getElementById('totalRevenue');
            if (totalRevenueEl) {
                totalRevenueEl.textContent = '₹' + (data.total_revenue || 0).toLocaleString('en-IN', {
                    maximumFractionDigits: 2,
                    minimumFractionDigits: 0
                });
            }
            
            // Update total bookings count
            const totalBookingsEl = document.getElementById('totalBookings');
            if (totalBookingsEl) {
                totalBookingsEl.textContent = (data.total_bookings || 0).toLocaleString('en-IN');
            }
            
            // Update today's revenue with formatted currency
            const todayRevenueEl = document.getElementById('todayRevenue');
            if (todayRevenueEl) {
                todayRevenueEl.textContent = '₹' + (data.today_revenue || 0).toLocaleString('en-IN', {
                    maximumFractionDigits: 2,
                    minimumFractionDigits: 0
                });
            }
            
            // Update today's bookings count
            const todayBookingsEl = document.getElementById('todayBookings');
            if (todayBookingsEl) {
                todayBookingsEl.textContent = (data.today_bookings || 0).toLocaleString('en-IN');
            }
        } catch (error) {
            console.error('Error loading stats:', error);
            this.showError('Failed to load statistics. Please try again.');
        }
    }

    /**
     * Load and render 30-day revenue trend chart
     * 
     * Fetches daily revenue data for the last 30 days
     * Renders as a line chart with smooth curves
     * 
     * API: GET /custom-admin/api/revenue/?days=30
     * Returns: {dates: [...], revenues: [...]}
     */
    async loadRevenue() {
        try {
            const params = this.buildFilterParams();
            const response = await fetch(`${this.apiBaseUrl}/revenue/?days=30&${params}`, {
                credentials: 'include'
            });
            if (!response.ok) {
                throw new Error(`Revenue API error: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Revenue data:', data);
            console.log('Revenue data received:', data);
            
            // Validate data
            if (!Array.isArray(data.dates) || !Array.isArray(data.revenues)) {
                throw new Error('Invalid revenue data format');
            }
            
            if (data.dates.length === 0 || data.revenues.length === 0) {
                console.warn('No revenue data available - creating empty chart');
                // Create empty chart with no data
                this.renderRevenueChart({ dates: [], revenues: [] });
                return;
            }
            
            console.log(`Revenue chart data: ${data.dates.length} dates, ${data.revenues.length} revenues`);
            this.renderRevenueChart(data);
        } catch (error) {
            console.error('Error loading revenue:', error);
            this.showError('Failed to load revenue chart.');
            // Still render empty chart
            this.renderRevenueChart({ dates: [], revenues: [] });
        }
    }

    /**
     * Load and render movies and bookings data
     * 
     * Fetches two datasets:
     * 1. Top 5 movies by booking count
     * 2. Recent 5 bookings with user, movie, amount info
     * 
     * API: GET /custom-admin/api/bookings/
     * Returns: {movies: [...], bookings: [...]}
     */
    async loadBookings() {
        try {
            const params = this.buildFilterParams();
            const [bookingsResponse, theatersResponse] = await Promise.all([
                fetch(`${this.apiBaseUrl}/bookings/?${params}`, {
                    credentials: 'include'
                }),
                fetch(`${this.apiBaseUrl}/theaters/?${params}`, {
                    credentials: 'include'
                })
            ]);
            
            if (!bookingsResponse.ok) {
                throw new Error(`Bookings API error: ${bookingsResponse.status}`);
            }
            
            const bookingsData = await bookingsResponse.json();
            console.log('Bookings data:', bookingsData);
            
            // Validate bookings data
            if (!Array.isArray(bookingsData.movies) || !Array.isArray(bookingsData.bookings)) {
                throw new Error('Invalid bookings data format');
            }
            
            // Render top movies bar chart
            this.renderMoviesChart(bookingsData.movies);
            // Populate recent bookings table
            this.renderBookingsTable(bookingsData.bookings);
            
            // Handle theaters data if available
            if (theatersResponse.ok) {
                const theatersData = await theatersResponse.json();
                if (Array.isArray(theatersData.theaters)) {
                    this.renderTheatersChart(theatersData.theaters);
                }
            }
        } catch (error) {
            console.error('Error loading bookings:', error);
            this.showError('Failed to load bookings and theater data.');
        }
    }

    /**
     * Render revenue trend line chart
     * 
     * Shows daily revenue over 30 days as a smooth line chart
     * Features:
     * - Filled area under the line
     * - Formatted Y-axis with rupee symbol and K abbreviation
     * - Tooltip on hover
     * - Responsive and maintains aspect ratio
     * 
     * @param {Object} data - {dates: string[], revenues: number[]}
     */
    renderRevenueChart(data) {
        const ctx = document.getElementById('revenueChart');
        if (!ctx) {
            console.error('Revenue chart canvas not found');
            return;
        }
        
        // Validate chart data
        if (!data || !data.dates || !data.revenues) {
            console.warn('No valid revenue data to render');
            return;
        }
        
        console.log(`Rendering revenue chart with ${data.dates.length} data points`);
        
        // Destroy previous chart instance to prevent memory leaks
        if (this.charts.revenue) {
            this.charts.revenue.destroy();
        }

        try {
            // Generate sample data if empty
            const hasData = data.dates.length > 0 && data.revenues.length > 0;
            const chartDates = hasData ? data.dates : this.generateSampleDates(30);
            const chartRevenues = hasData ? data.revenues : this.generateSampleRevenues(30);
            
            // Create new line chart with gradient styling
            this.charts.revenue = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    // Format dates to 'Mon 10' format for readability
                    labels: chartDates.map(d => {
                        const date = new Date(d + 'T00:00:00');
                        return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
                    }),
                    datasets: [{
                        label: 'Revenue (₹)',
                        data: chartRevenues.map(v => Math.max(0, v)),
                        borderColor: '#667eea',  // Line color
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',  // Fill color
                        fill: true,
                        tension: 0.4,  // Smooth curves
                        pointRadius: 4,  // Data point size
                        pointBackgroundColor: '#667eea',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        legend: { 
                            display: true, 
                            position: 'top',
                            labels: {
                                font: { size: 12, weight: '600' },
                                padding: 15,
                                usePointStyle: true,
                            }
                        },
                        filler: { propagate: true },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 },
                            cornerRadius: 6,
                            displayColors: true,
                            callbacks: {
                                label: (context) => {
                                    const value = context.parsed.y || 0;
                                    return 'Revenue: ₹' + value.toLocaleString('en-IN', { maximumFractionDigits: 0 });
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                            ticks: {
                                // Format large numbers with K abbreviation
                                callback: (v) => {
                                    if (v >= 1000) {
                                        return '₹' + (v / 1000).toFixed(0) + 'k';
                                    }
                                    return '₹' + v;
                                },
                                font: { size: 11 },
                                color: '#858796',
                                padding: 8,
                            }
                        },
                        x: {
                            grid: { display: false, drawBorder: false },
                            ticks: { 
                                font: { size: 11 },
                                color: '#858796',
                                padding: 8,
                            }
                        }
                    }
                }
            });
            
            console.log('Revenue chart rendered successfully');
        } catch (error) {
            console.error('Error rendering revenue chart:', error);
            this.showError('Failed to render revenue chart.');
        }
    }
    
    /**
     * Generate sample dates for display when no data available
     */
    generateSampleDates(days) {
        const dates = [];
        const end = new Date();
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(end);
            date.setDate(date.getDate() - i);
            dates.push(date.toISOString().split('T')[0]);
        }
        return dates;
    }
    
    /**
     * Generate sample revenues for display when no data available
     */
    generateSampleRevenues(days) {
        return Array(days).fill(0);
    }
                        borderColor: '#667eea',  // Line color
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',  // Fill color
                        fill: true,
                        tension: 0.4,  // Smooth curves
                        pointRadius: 4,  // Data point size
                        pointBackgroundColor: '#667eea',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        legend: { 
                            display: true, 
                            position: 'top',
                            labels: {
                                font: { size: 12, weight: '600' },
                                padding: 15,
                                usePointStyle: true,
                            }
                        },
                        filler: { propagate: true },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 },
                            cornerRadius: 6,
                            displayColors: true,
                            callbacks: {
                                label: (context) => {
                                    const value = context.parsed.y || 0;
                                    return 'Revenue: ₹' + value.toLocaleString('en-IN', { maximumFractionDigits: 0 });
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                            ticks: {
                                // Format large numbers with K abbreviation
                                callback: (v) => {
                                    if (v >= 1000) {
                                        return '₹' + (v / 1000).toFixed(0) + 'k';
                                    }
                                    return '₹' + v;
                                },
                                font: { size: 11 },
                                color: '#858796',
                                padding: 8,
                            }
                        },
                        x: {
                            grid: { display: false, drawBorder: false },
                            ticks: { 
                                font: { size: 11 },
                                color: '#858796',
                                padding: 8,
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering revenue chart:', error);
            this.showError('Failed to render revenue chart.');
        }
    }

    /**
     * Render top movies bar chart
     * 
     * Shows top 5 movies by booking count as a horizontal bar chart
     * Green color highlighting top performers
     * 
     * @param {Array} movies - [{title, bookings}, ...]
     */
    renderMoviesChart(movies) {
        const ctx = document.getElementById('moviesChart');
        if (!ctx) return;
        
        // Validate movie data
        if (!Array.isArray(movies) || movies.length === 0) {
            console.warn('No movie data to render');
            console.log('Movie data received:', movies);
            return;
        }
        
        console.log('Rendering movies chart with data:', movies);
        
        // Clean up previous instance
        if (this.charts.movies) {
            this.charts.movies.destroy();
        }

        try {
            // Create bar chart for top movies
            this.charts.movies = new Chart(ctx.getContext('2d'), {
                type: 'bar',
                data: {
                    // Display full movie titles
                    labels: movies.map(m => {
                        if (!m.title) return 'Unknown';
                        // Truncate to reasonable length for display
                        return m.title.length > 20 ? m.title.substring(0, 20) + '...' : m.title;
                    }),
                    datasets: [{
                        label: 'Bookings',
                        data: movies.map(m => Math.max(0, m.bookings || 0)),
                        backgroundColor: '#1cc88a',  // Green for positive metric
                        borderRadius: 6,
                        borderSkipped: false,
                        hoverBackgroundColor: '#17a66f',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',  // Horizontal bar chart
                    plugins: {
                        legend: { 
                            display: true, 
                            position: 'top',
                            labels: { 
                                font: { size: 12, weight: '600' }, 
                                padding: 15,
                                usePointStyle: true,
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            cornerRadius: 6,
                            callbacks: {
                                label: (context) => {
                                    return 'Bookings: ' + (context.parsed.x || 0).toLocaleString('en-IN');
                                }
                            }
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true,
                            grid: { display: false, drawBorder: false },
                            ticks: { 
                                font: { size: 11 },
                                color: '#858796',
                            }
                        },
                        x: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                            ticks: { 
                                font: { size: 11 },
                                color: '#858796',
                                callback: (v) => (v || 0).toLocaleString('en-IN'),
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering movies chart:', error);
            this.showError('Failed to render movies chart.');
        }
    }

    /**
     * Render top theaters bar chart
     * 
     * Shows top 5 theaters by revenue as a bar chart
     * Cyan/blue color for revenue metrics
     * 
     * @param {Array} theaters - [{name, bookings, revenue}, ...]
     */
    renderTheatersChart(theaters) {
        const ctx = document.getElementById('theatersChart');
        if (!ctx) return;
        
        // Validate theater data
        if (!Array.isArray(theaters) || theaters.length === 0) {
            console.warn('No theater data to render');
            console.log('Theater data received:', theaters);
            return;
        }
        
        console.log('Rendering theaters chart with data:', theaters);
        
        // Clean up previous instance
        if (this.charts.theaters) {
            this.charts.theaters.destroy();
        }

        try {
            // Create bar chart for top theaters
            this.charts.theaters = new Chart(ctx.getContext('2d'), {
                type: 'bar',
                data: {
                    // Display full theater names
                    labels: theaters.map(t => {
                        if (!t.name) return 'Unknown';
                        // Truncate to reasonable length for display
                        return t.name.length > 20 ? t.name.substring(0, 20) + '...' : t.name;
                    }),
                    datasets: [{
                        label: 'Revenue (₹)',
                        data: theaters.map(t => Math.max(0, t.revenue || 0)),
                        backgroundColor: '#36b9cc',  // Cyan for revenue
                        borderRadius: 6,
                        borderSkipped: false,
                        hoverBackgroundColor: '#2aa5ba',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',  // Horizontal bar chart
                    plugins: {
                        legend: { 
                            display: true, 
                            position: 'top',
                            labels: { 
                                font: { size: 12, weight: '600' }, 
                                padding: 15,
                                usePointStyle: true,
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            cornerRadius: 6,
                            callbacks: {
                                label: (context) => {
                                    const value = context.parsed.x || 0;
                                    return 'Revenue: ₹' + value.toLocaleString('en-IN', { maximumFractionDigits: 0 });
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { display: false, drawBorder: false },
                            ticks: { 
                                font: { size: 11 },
                                color: '#858796',
                            }
                        },
                        x: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.05)', drawBorder: false },
                            ticks: {
                                font: { size: 11 },
                                color: '#858796',
                                callback: (v) => {
                                    if (v >= 1000) {
                                        return '₹' + (v / 1000).toFixed(0) + 'k';
                                    }
                                    return '₹' + v;
                                }
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering theaters chart:', error);
            this.showError('Failed to render theaters chart.');
        }
    }

    renderBookingsTable(bookings) {
        const tbody = document.getElementById('bookingsTable');
        if (!tbody) return;
        
        if (!Array.isArray(bookings) || bookings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted"><em>No bookings found</em></td></tr>';
            return;
        }

        try {
            tbody.innerHTML = bookings.map(b => {
                // Validate booking object
                const user = this.escapeHtml(b.user || 'Unknown');
                const movie = this.escapeHtml((b.movie || 'Unknown').substring(0, 25));
                const amount = (b.amount || 0).toLocaleString('en-IN', { 
                    maximumFractionDigits: 2,
                    minimumFractionDigits: 0
                });
                
                return `
                    <tr>
                        <td><strong>${user}</strong></td>
                        <td title="${this.escapeHtml(b.movie || 'Unknown')}" style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            ${movie}
                        </td>
                        <td class="text-end">₹${amount}</td>
                    </tr>
                `;
            }).join('');
        } catch (error) {
            console.error('Error rendering bookings table:', error);
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-danger">Error loading bookings</td></tr>';
        }
    }

    escapeHtml(text) {
        if (typeof text !== 'string') {
            return '';
        }
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing AdminDashboard...');
    try {
        const dashboard = new AdminDashboard();
        console.log('AdminDashboard initialized successfully');
    } catch (error) {
        console.error('Failed to initialize AdminDashboard:', error);
    }
});
