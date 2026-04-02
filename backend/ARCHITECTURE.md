You are a senior backend engineer. Build a production-ready backend for a "Queue-less Pre-order & Pickup System" using FastAPI.

## 🧱 TECH STACK

* FastAPI (async)
* PostgreSQL (SQLAlchemy ORM)
* Redis (caching + Celery broker)
* Celery (background jobs)
* JWT Authentication (role-based)
* WebSockets (for real-time updates)
* Paystack (payment integration via webhooks)
* Cloudinary (file storage - optional for now)

---

## 🎯 SYSTEM OVERVIEW

This system allows:

* Customers to pre-order and pay for food/items
* Merchants to receive and process orders
* Admins to manage the platform

The goal is to eliminate queues by enabling "Order → Pay → Pickup".

---

## 👥 USER ROLES (RBAC)

Implement Role-Based Access Control with 3 roles:

* CUSTOMER
* MERCHANT
* ADMIN

Each user must have:

* id
* email
* password (hashed)
* role
* is_active
* created_at

---

## 🗄️ DATABASE MODELS

Design models with SQLAlchemy:

### User

* id (UUID)
* email (unique)
* password_hash
* role (enum: customer, merchant, admin)
* is_active
* created_at

### Store

* id
* name
* description
* owner_id (FK → User)
* location
* is_active
* created_at

### Product

* id
* store_id (FK)
* name
* description
* price
* is_available
* image_url (optional)
* created_at

### Order

* id
* user_id (FK)
* store_id (FK)
* total_amount
* status (pending, paid, preparing, ready, completed, cancelled)
* payment_reference (unique)
* created_at

### OrderItem

* id
* order_id (FK)
* product_id (FK)
* quantity
* price

### Payment

* id
* order_id (FK)
* reference (unique)
* status (pending, success, failed)
* amount
* provider ("paystack")
* created_at

---

## 🔐 AUTHENTICATION

* Implement JWT authentication
* Login endpoint returns access + refresh tokens
* Password hashing using bcrypt
* Middleware/dependency to enforce roles

Example:

* Only merchants can manage products
* Only customers can create orders
* Admin can access everything

---

## 📡 API ENDPOINTS

### Auth

* POST /api/v1/auth/register
* POST /api/v1/auth/login
* GET /api/v1/auth/me

---

### Stores

* GET /api/v1/stores
* POST /api/v1/stores (merchant only)
* GET /api/v1/stores/{id}
* PUT /api/v1/stores/{id}
* DELETE /api/v1/stores/{id}

---

### Products

* GET /api/v1/stores/{id}/products
* POST /api/v1/products (merchant only)
* PUT /api/v1/products/{id}
* DELETE /api/v1/products/{id}

---

### Orders

* POST /api/v1/orders (customer only)
* GET /api/v1/orders/{id}
* GET /api/v1/orders (filter by user/store)
* PATCH /api/v1/orders/{id}/status (merchant only)

---

### Payments

* POST /api/v1/payments/initiate
* POST /api/v1/payments/webhook (Paystack)

---

## 💳 PAYMENTS (PAYSTACK)

* When order is created → generate payment reference
* Call Paystack API to initialize transaction
* Store reference in DB
* Handle webhook:

  * Verify signature
  * Confirm payment
  * Update order status to "paid"
  * Ensure idempotency (no duplicate processing)

---

## 🔄 ORDER FLOW

Valid transitions:

* pending → paid → preparing → ready → completed
* pending → cancelled

Enforce this logic in backend.

---

## 🔔 BACKGROUND TASKS (CELERY)

Implement Celery with Redis:

Tasks:

* Verify payment (backup)
* Send notifications (stub for now)
* Expire unpaid orders (after 10 mins)
* Retry failed tasks

---

## ⚡ REDIS USAGE

* Cache store menus
* Rate limiting
* Celery broker

---

## 🔌 WEBSOCKETS

* Implement WebSocket endpoint:

  * Notify merchants of new orders
  * Notify customers when order status changes

---

## 🔐 SECURITY

* Validate all inputs using Pydantic
* Use environment variables for secrets
* Enable CORS
* Rate limit critical endpoints

---

## 🧾 QR CODE SYSTEM

* Generate QR code for each order
* QR contains order ID or URL
* Endpoint to validate scanned QR

---

## 📊 LOGGING

* Basic structured logging
* Log:

  * Order creation
  * Payment events
  * Errors

---

## 🧱 PROJECT STRUCTURE

Organize code like:

/app
/api
/models
/schemas
/services
/core
/tasks
/db
main.py

---

## 🚀 REQUIREMENTS

* Use async where appropriate
* Keep code modular and clean
* Use dependency injection
* Include comments for clarity
* Ensure production-level structure

---

## 🎯 OUTPUT EXPECTATION

Generate:

* Full FastAPI project structure
* Models, schemas, routers
* Auth system with JWT
* Sample Celery setup
* WebSocket example
* Paystack integration (mock if needed)

Do NOT skip implementation details.
Write clean, scalable, maintainable code.

