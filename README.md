# 🍽️ Amrita Canteen Management System (CMS)

A modern, full-stack multi-canteen ordering and kitchen queue management web application designed for campus environments. Built with **React 19 + Vite** on the frontend and **Django REST Framework (DRF) + PostgreSQL** on the backend.

---

## 🚀 Demo User Credentials (User Perspective)

To experience the application from a regular customer/student perspective:

| Field | Credentials |
|---|---|
| **URL** | `http://localhost:5173/login` |
| **Username** | `deepak` |
| **Password** | `1234567890` |
| **Role** | User / Customer Perspective |

> **Note:** You can also register a brand-new user account anytime by clicking **SignUp** on the login page.

---

## 🧭 User Perspective Walkthrough

Once logged in with `deepak`, here is the typical customer workflow:

```
[Login] ──► [Select Canteen] ──► [Browse Menu & Stock] ──► [Add to Cart] ──► [Place Order] ──► [Track Live Status]
```

1. **Sign In**:
   - Navigate to `/login`.
   - Enter `deepak` and `1234567890` to authenticate.
   - Secure JWT tokens (`access` & `refresh`) are automatically managed in the background.

2. **Select Campus Canteen**:
   - After login, you are redirected to `/home`.
   - Choose from available canteens:
     - 🏛️ **Main Canteen (SOPANAM)** — Near AB1
     - 💻 **IT Canteen** — Near AB3
     - 🎓 **MBA Canteen** — Near Business School

3. **Browse Menu & Real-time Stock**:
   - Filter items by category: **Beverages**, **Snacks**, and **Meals**.
   - Check real-time stock levels, item prices, and dish pictures.

4. **Manage Cart**:
   - Add items and adjust item quantities.
   - Cart is scoped to the selected canteen to ensure streamlined kitchen fulfillment.

5. **Place Order**:
   - Review cart summary and checkout.
   - Orders are registered immediately in the backend.

6. **Order Tracking & Status**:
   - Navigate to `/orders` from the header menu.
   - View current and previous orders with live status progression:
     - 🟡 `Pending` ➔ 🟠 `Preparing` ➔ 🟢 `Prepared` ➔ 🔵 `Delivered`
   - Real-time waiting time estimation informs you when your food is ready for pickup.

---

## 🛠️ Tech Stack

### Frontend
- **Framework:** React 19 with Vite 7
- **Routing:** React Router v7 (`react-router-dom`)
- **Styling:** Modular Vanilla CSS with skeleton loading states & responsive layouts
- **HTTP Client:** Axios & Fetch API with JWT Bearer Token interception
- **State & Utilities:** JWT Decode, Day.js, Supabase JS Client

### Backend
- **Framework:** Django 5.2 & Django REST Framework (DRF)
- **Authentication:** SimpleJWT (JSON Web Tokens) with automated refresh
- **Database:** PostgreSQL (Supabase-hosted or local) / SQLite fallback
- **Email Notifications:** Brevo SMTP Integration
- **Server / Deployment:** Gunicorn, WhiteNoise, CORS Headers

---

## 📁 Repository Structure

```
team_name_pending/
├── canteen-frontend/            # React + Vite client
│   ├── src/
│   │   ├── assets/              # Images, icons, background assets
│   │   ├── components/          # Header, CartItem, Skeletons, Modals
│   │   ├── config/              # Centralized API baseURL config
│   │   ├── pages/
│   │   │   ├── Admin/           # Admin dashboard, menus & analytics
│   │   │   ├── Auth/            # Login & SignUp components
│   │   │   ├── Cart/            # Cart page & checkout
│   │   │   ├── Home/            # Canteen selection hub
│   │   │   ├── menu/            # Menu listing & item filters
│   │   │   └── Orders/          # Live order tracking page
│   │   ├── App.jsx              # Application routing table
│   │   └── main.jsx             # React DOM root entrypoint
│   ├── .env.example             # Frontend environment variables template
│   └── package.json
│
├── myproject/                   # Django REST Framework backend
│   ├── Canteen_backend/         # Core application
│   │   ├── models.py            # Canteen, Product, Menu, Cart, Order models
│   │   ├── views.py             # DRF ViewSets & custom business endpoints
│   │   ├── serializers.py       # Model serializers
│   │   └── urls.py              # API endpoint routes
│   ├── myproject/               # Project configuration (settings, wsgi, asgi)
│   ├── manage.py                # Django management utility
│   ├── populate_roles.py        # Staff/Admin/User role assignment script
│   ├── seed_data.py             # Database seeder with sample data
│   ├── .env.example             # Backend environment template
│   └── requirements.txt         # Python dependencies
│
├── WAITING_TIME_DESIGN.md       # Kitchen waiting-time algorithm design
├── requirements.txt             # Root requirements definition
└── README.md                    # Project documentation
```

---

## 💻 Local Setup & Installation

### 1. Prerequisites
- **Node.js** (v18.x or later) & `npm`
- **Python** (v3.10 or later) & `pip`
- **Git**

---

### 2. Backend Setup (Django)

1. Open your terminal and change directory to `myproject`:
   ```bash
   cd myproject
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Create a `.env` file inside `myproject/` based on `.env.example`:
     ```env
     DJANGO_SECRET_KEY=your-django-secret-key
     DJANGO_DEBUG=True
     DB_NAME=postgres
     DB_USER=your-db-username
     DB_PASSWORD=your-db-password
     DB_HOST=your-db-host
     DB_PORT=5432
     ```

5. Apply database migrations:
   ```bash
   python manage.py migrate
   ```

6. *(Optional)* Seed initial sample users, canteens, and products:
   ```bash
   python seed_data.py
   python populate_roles.py
   ```

7. Start the backend development server:
   ```bash
   python manage.py runserver
   ```
   > Backend will run at: `http://127.0.0.1:8000`

---

### 3. Frontend Setup (React + Vite)

1. Open a second terminal window and navigate to `canteen-frontend`:
   ```bash
   cd canteen-frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   - Create `.env` based on `.env.example`:
     ```env
     VITE_API_BASE_URL=http://127.0.0.1:8000
     ```

4. Launch Vite development server:
   ```bash
   npm run dev
   ```
   > Frontend will be available at: `http://localhost:5173`

---

## 🔑 Key API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/login/` | `POST` | Authenticate user & receive JWT tokens |
| `/api/token/refresh/` | `POST` | Refresh expired access token |
| `/api/canteens/` | `GET` | List all available canteens |
| `/api/canteens/<canteen_id>/menu/` | `GET` | Get active menu & stock for a canteen |
| `/api/cart/` | `GET`, `POST` | View and manage current user's cart |
| `/api/orders/` | `GET`, `POST` | Place orders and view order history |
| `/api/orders/<order_id>/` | `GET` | View individual order status and estimated time |

---

## 👥 Contributors & Team
Developed by **Team Name Pending** for the Amrita Canteen Management Project.
