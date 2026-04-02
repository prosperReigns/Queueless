You are a senior frontend engineer. Build a production-ready frontend for a "Queue-less Pre-order & Pickup System".

## 🧱 TECH STACK

* React (with Vite)
* Tailwind CSS
* React Router
* React Query (TanStack Query)
* Axios (API calls)
* Context API (auth state)
* WebSockets (real-time updates)
* Firebase Cloud Messaging (push notifications)

---

## 🎯 SYSTEM OVERVIEW

This app allows:

* Customers to browse stores, order, and pay
* Merchants to manage products and process orders
* Admins to manage the platform

Focus on performance, simplicity, and mobile-first design (Nigeria context).

---

## 👥 USER ROLES

Implement role-based UI for:

* CUSTOMER
* MERCHANT
* ADMIN

Each role sees different dashboards and routes.

---

## 📁 PROJECT STRUCTURE

Organize code like:

/src
/api        (axios setup, API calls)
/components (reusable UI components)
/features
/auth
/stores
/products
/orders
/dashboard
/hooks
/layouts
/pages
/routes
/context
/utils
/services   (websocket, firebase)
App.jsx
main.jsx

---

## 🔐 AUTHENTICATION

* JWT-based auth
* Store token in memory + localStorage
* Auth Context:

  * user
  * role
  * login/logout

Pages:

* Login
* Register

Protect routes:

* Customer routes
* Merchant routes
* Admin routes

---

## 🌐 API INTEGRATION

* Use Axios instance with base URL
* Attach JWT token to headers
* Handle errors globally (interceptors)

---

## ⚡ STATE MANAGEMENT

Use React Query for:

* Fetching stores
* Fetching products
* Orders
* Mutations (create/update)

---

## 📱 CUSTOMER FEATURES

### Pages:

* Home (list of stores)
* Store Details (menu)
* Cart
* Checkout
* Order Confirmation (QR Code)
* My Orders

### Features:

* Browse stores
* View products
* Add to cart
* Place order
* Pay (redirect to Paystack)
* View order status
* QR code display

---

## 🧑‍🍳 MERCHANT FEATURES

### Pages:

* Dashboard
* Orders Management
* Product Management
* Store Settings

### Features:

* View incoming orders (real-time)
* Update order status:

  * Preparing
  * Ready
  * Completed
* Add/Edit/Delete products
* Toggle product availability

---

## 🛠️ ADMIN FEATURES (basic)

* View all users
* View all stores
* Basic analytics (optional placeholder)

---

## 🔔 REAL-TIME FEATURES

* Use WebSockets:

  * Merchant gets new order alerts
  * Customer gets order status updates

Fallback:

* Polling using React Query

---

## 🔔 PUSH NOTIFICATIONS

Integrate Firebase Cloud Messaging:

* Request notification permission
* Receive messages
* Show alerts for:

  * Order ready
  * New order (merchant)

---

## 🧾 QR CODE

* Display QR code on order confirmation page
* Use order ID or URL
* Ensure it is large and scannable

---

## 🎨 UI/UX REQUIREMENTS

* Mobile-first design
* Clean, minimal UI
* Fast loading
* Clear call-to-actions

Use Tailwind:

* Cards
* Buttons
* Modals
* Status badges

---

## 🧩 REUSABLE COMPONENTS

* Navbar
* Sidebar (merchant)
* ProductCard
* OrderCard
* Loader
* Modal
* ProtectedRoute

---

## 🔄 ORDER STATUS UI

Show clear states:

* Pending
* Paid
* Preparing
* Ready
* Completed

Use color indicators.

---

## ⚠️ ERROR HANDLING

* Show user-friendly messages
* Handle:

  * Network errors
  * Payment failures
  * Empty states

---

## 🔐 SECURITY

* Protect routes
* Do not expose sensitive data
* Handle token expiration

---

## 🚀 PERFORMANCE

* Lazy load pages
* Optimize API calls
* Use caching (React Query)

---

## 🎯 OUTPUT EXPECTATION

Generate:

* Full React project structure
* Routing setup
* Auth context
* API integration
* Pages for customer + merchant
* Sample components
* WebSocket integration example
* Firebase notification setup (basic)

Keep code clean, modular, and production-ready.
Do NOT skip important parts.

note: variant used is typescript + react compiler
