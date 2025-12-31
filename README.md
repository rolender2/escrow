# Repair Escrow Automation Platform

A Full-Stack MVP for Real Estate Agents to manage post-inspection repair holdbacks.
This platform allows agents to "Close Now, Fix Later" by automating the fund release process based on Inspector approvals.

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
# Install dependencies (incl. pymongo)
conda run -n ai pip install -r requirements.txt
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

## Documentation & Reports
*   **[User Acceptance Testing (UAT)](user-acceptance-testing.md)**: Step-by-step test cases.
*   **[Business Assessment Report](escrow_automation_assessment.md)**: Original market analysis and business case.
*   **[Prototype Walkthrough](prototype_walkthrough.md)**: Technical architecture overview.

## Key Features

### 1. For Real Estate Agents
*   **"Close Now, Fix Later"**: Instantly create a secure holdback agreement to save a deal at the closing table.
*   **Dashboard View**: Track all active repair escrows, their amounts, and status in real-time.
*   **Funds Locking**: Automatically sets the escrow state to `CREATED` -> `FUNDED` (via Custodian Confirmation) -> `ACTIVE`.

### 2. For Contractors
*   **Clear Requirements**: See exactly what evidence (e.g., "Photo", "Invoice") is required to get paid.
*   **Evidence Upload Portal**: Simple interface to upload proofs directly to the specific milestone.
*   **Transparency**: Real-time status updates so they know when funds are approved.

### 3. For Inspectors / Approvers
*   **Digital Approval**: One-click "Approve Release" button that is only enabled when all evidence conditions are met.
*   **Security**: Prevents accidental releases by enforcing evidence checks before the approval action is available.

### 4. The "Rule Engine" (Backend)
*   **Hybrid Architecture**: Uses **PostgreSQL** for state management and **MongoDB** for the immutable ledger.
*   **State Machine**: Rigorous logic enforcing the lifecycle: `Created` -> `Funded` -> `WorkDone` -> `Approved` -> `Paid`.
*   **Non-Custodial Logic**: The system generates a **Banking Instruction** (JSON) for the title company/custodian to execute, ensuring the platform never touches the money directly.
*   **Audit Explorer**: A transparent UI (`/audit`) visualizing the cryptographic chain of all events (`prev_hash` -> `current_hash`), providing a verifiable history of every action.

## License
Proprietary / Prototype.
