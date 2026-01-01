# VeriDraw Protocol (formerly Repair Escrow)
Domain: [veridraw.ai](https://veridraw.ai)

The **Trust Protocol for Construction**.
A milestone-based payment platform for Builders, Lenders, and Homeowners. Funds are secured cryptographically and released only when work is proven.

## Project Structure
*   **`frontend/`**: Next.js 14 Dashboard (React, TailwindCSS).
*   **`backend/`**: FastAPI REST API (Python, SQLAlchemy).
*   **`rule_engine_proto/`**: Original CLI Prototype (Python script).
*   **`user-guide.md`**: Step-by-step usage instructions.

## Quick Start

### 1. Prerequisites
*   Node.js & npm
*   Python 3.10+
*   PostgreSQL (`escrow_db`) - *Stores State*
*   MongoDB (`escrow_ledger`) - *Stores Immutable Audit Logs*

### 2. Backend Setup (Port 8000)
**Configuration**:
Ensure you have a `.env` file in `backend/` with your PostgreSQL credentials:
```env
POSTGRES_USER=robert
POSTGRES_PASSWORD=...
POSTGRES_DB=escrow_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

**Run Server**:
```bash
cd backend
# Install dependencies (incl. pymongo, jose, passlib)
conda run -n ai pip install -r requirements.txt
# Seed Default Users (REQUIRED for Login)
conda run -n ai python seed_users.py
# Start the API
conda run -n ai uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*   **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Start Frontend (Port 3000)
```bash
cd frontend
npm install
npm run dev
```
Dashboard: [http://localhost:3000](http://localhost:3000)

## Default Users (Test Harness)
The system comes seeded with role-based users. Password for all is `password123`.

| User | Username | Role | Function |
| :--- | :--- | :--- | :--- |
| **Agent** | `alice_agent` | `AGENT` | Create Agreements |
| **Contractor** | `bob_contractor` | `CONTRACTOR` | Upload Evidence |
| **Inspector** | `jim_inspector` | `INSPECTOR` | Approve Release |
| **Custodian** | `title_co` | `CUSTODIAN` | Confirm Wire (One-Time) |
| **Admin** | `admin` | `ADMIN` | System Ops |

## Key Features

### 1. Secure Identity & Authority
*   **JWT Authentication**: Full session management with persistent login.
*   **Strict RBAC**: Server-side enforcement of who can do what (e.g., Contractors cannot approve payments).
*   **One-Time Gates**: Critical actions like "Confirm Funds" are cryptographically locked to happen only once.

### 2. For Lenders & Homeowners
*   **"Pay on Progress"**: Funds are never released without proof.
*   **Dashboard View**: Track all active construction draws and approvals in real-time.

### 3. For Builders & Contractors
*   **Clear Requirements**: See exactly what evidence (e.g., "Photo", "Invoice") is required to get paid.
*   **Evidence Upload Portal**: Simple interface to upload proofs directly to the specific milestone.

### 4. For Inspectors / Approvers
*   **Digital Approval**: One-click "Approve Release" button that is only enabled when all evidence conditions are met.
*   **Security**: Prevents accidental releases by enforcing evidence checks before the approval action is available.

### 5. The "Rule Engine" (Backend)
*   **Hybrid Architecture**: Uses **PostgreSQL** for state management and **MongoDB** for the immutable ledger.
*   **State Machine**: Rigorous logic enforcing the lifecycle: `Created` -> `Funded` -> `WorkDone` -> `Approved` -> `Paid`.
*   **Ledger-First**: All events are purely additive "Attestations" written to the immutable log *before* state changes.
*   **Audit Explorer**: A transparent UI (`/audit`) visualizing the cryptographic chain of all events (`prev_hash` -> `current_hash`).

## License
Proprietary / Prototype.
