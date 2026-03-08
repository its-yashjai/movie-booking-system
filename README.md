# 🎬 Movie Booking System

[![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django)](https://www.djangoproject.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap)](https://getbootstrap.com/)
[![Redis](https://img.shields.io/badge/Redis-7.x-DC382D?logo=redis)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A comprehensive movie ticket booking platform built with Django. Real-time seat selection, Razorpay payment integration, and Redis-based concurrency control.

---

## ✨ Features

- 🎥 Movie & theater management
- 🪑 Real-time interactive seat selection
- 🔒 Redis-based seat locking (anti-double booking)
- 💳 Razorpay payment integration
- 📧 Email notifications with SendGrid
- 📱 Fully responsive design
- 🎨 Modern dark theme UI
- ⚙️ Admin dashboard with analytics
- 🔐 Rate limiting & security

---

## 🛠️ Tech Stack

| Component | Technology |
| --- | --- |
| Backend | Django 4.2, Python 3.9+ |
| Database | SQLite / PostgreSQL |
| Cache | Redis 7.x |
| Payments | Razorpay |
| Email | SendGrid |
| Frontend | Bootstrap 5, JavaScript |
| Deployment | Docker, Gunicorn |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Redis running locally
- PostgreSQL (for production)

### Installation

```bash
# Clone repository
git clone https://github.com/its-yashjai/movie-booking-clone.git
cd movie-booking-clone

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Visit: `http://localhost:8000`

---

## 📁 Project Structure

```
movie-booking-system/
├── accounts/           # User authentication & profiles
├── bookings/          # Booking & payment management
├── movies/            # Movie & theater data
├── custom_admin/      # Admin dashboard
├── templates/         # HTML templates
├── static/            # CSS & JavaScript
├── manage.py          # Django CLI
└── requirements.txt   # Dependencies
```

---

## 🔑 Key Components

### Seat Locking
- Redis-based locks prevent double bookings
- Automatic timeout after 10 minutes
- Real-time seat availability updates

### Payment Processing
- Razorpay integration for secure payments
- Order creation and verification
- Email confirmations

### Email System
- SendGrid backend for reliable delivery
- Booking confirmations
- Payment notifications

---

## 📝 API Endpoints

- `GET /` - Home page
- `GET /movies/` - Movie listing
- `GET /movies/<id>/` - Movie details
- `POST /bookings/` - Create booking
- `GET /bookings/` - User bookings
- `/admin/` - Admin dashboard

---

## 🔒 Security Features

- Django security middleware
- CSRF protection
- SQL injection prevention
- Rate limiting on sensitive endpoints
- Email verification for accounts

---

## 📜 License

MIT License - Feel free to use this project for personal or commercial purposes.

---

## 💡 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.
