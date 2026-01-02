# User Acceptance Testing (UAT) Guide
**Project**: Programable Escrow Automation Platform (MVP)
**Version**: 2.0 (Secure & Role-Based)

This guide provides step-by-step scenarios to verify the functionality of the Escrow Platform. Use the specific **Test Data** provided to ensure consistent results.

---

## 🏗️ Prerequisites
*   **Backend**: Running on `http://localhost:8000` (FastAPI + MongoDB Ledger)
*   **Frontend**: Running on `http://localhost:3000` (Next.js)
*   **Database**: Seeded with users (`python seed_users.py`).

---

## 🧪 Scenario 1: The "Happy Path" (Secure Lifecycle)
**Goal**: Verify the standard lifecycle of a repair escrow with strict role enforcement.

### Step 1: Real Estate Agent Creates Agreement
1.  Navigate to **Landing Page** (`http://localhost:3000`).
2.  Click **"Log In"** (Top right) or **"Start an Escrow"**.
3.  **Login** as **Agent (Alice)** using the Quick Fill button.
4.  **Verify Redirect**: You are redirected to the **Dashboard** (`/dashboard`).
3.  Click **"+ New Repair Escrow"**.
4.  **Enter Test Data**:
    *   **Buyer (Client)**: `Alice Buyer`
    *   **Service Provider (Contractor)**: `Robs Roof`
    *   **Amount ($)**: `5000`
    *   **Repair Item**: `Roof Repair - North Wing`
5.  Click **"Create & Lock Funds"**.
6.  **Verify**:
    *   New Item appears with State: **`CREATED`** (Amber Badge).
    *   **Header Banner**: Shows "Logged in as: alice_agent [AGENT]".
7.  **Logout** (Click "Sign Out" in header).

### Step 2: Custodian Confirms Funds (The Gate)
1.  **Login** as **Custodian (TitleCo)** (via Landing Page -> Log In).
2.  Click on the newly created Escrow.
3.  **Action**: Click **"(Simulate) Confirm Wire Received"**.
4.  **Verify**:
    *   State changes to **`FUNDED`** (Blue Badge).
    *   Audit Log records the "One-Time Confirmation".
5.  **Logout**.

### Step 3: Contractor Uploads Evidence
1.  **Login** as **Contractor (Bob)**.
2.  Navigate to the Escrow -> Scroll to "Milestones".
3.  **Action**: In the "Roof Repair" milestone, click **Upload** (auto-fills URL).
4.  **Verify**:
    *   Milestone Status changes to **`EVIDENCE_SUBMITTED`**.
    *   "Approve Release" button becomes visible/enabled.
5.  **Logout**.

### Step 4: Inspector Approves Release
1.  **Login** as **Inspector (Jim)**.
2.  Navigate to the Escrow -> Milestones.
3.  **Action**: Click **"Approve Release"**.
4.  **Verify**:
    *   Milestone Status changes to **`PAID`** (Green).
    *   **Success!** The logic has generated the Banking Instruction internally.

---

## 🕵️ Scenario 2: Tamper-Evident Audit Trail
**Goal**: Verify that the system captured a tamper-evident audit trail of Scenario 1.

1.  **Login** as **Agent (Alice)** (or any user).
2.  Navigate to **Dashboard** -> Click **"View Ledger"** (Top right).
3.  **Verify the Chain** (Read from bottom to top):
    *   **Entry 1 (Genesis)**:
        *   Event: `CREATE`, Actor: `alice_agent`, Role: `AGENT`.
    *   **Entry 2**:
        *   Event: `CONFIRM_FUNDS`, Actor: `title_co`, Role: `CUSTODIAN`.
    *   **Entry 3**:
        *   Event: `UPLOAD_EVIDENCE`, Actor: `bob_contractor`, Role: `CONTRACTOR`.
    *   **Entry 4**:
        *   Event: `APPROVE`, Actor: `jim_inspector`, Role: `INSPECTOR`.
    *   **Entry 5 (Latest)**:
        *   Event: `PAYMENT_RELEASED`, Actor: `SYSTEM_instruction`, Role: `SYSTEM`.
4.  **Pass Criteria**: The `Previous Hash` of every entry strictly matches the `Current Hash` of the one below it.

---

## 🛡️ Scenario 3: Rule-Enforced Fund Control
**Goal**: Verify automated compliance rules (Users cannot perform actions outside their role).

### Test A: Contractor Cannot Approve
1.  **Login** as **Contractor (Bob)**.
2.  Find a milestone that is ready for approval (`EVIDENCE_SUBMITTED`).
3.  **Action**: Try to click **"Approve Release"** (if visible) or manually call API.
    *   *Note*: The UI might hide the button for non-Inspectors, but if visible...
4.  **Verify**: Backend returns `403 Forbidden` ("Operation not permitted for role CONTRACTOR").

### Test B: Agent Cannot Confirm Funds
1.  **Login** as **Agent (Alice)**.
2.  Find a `CREATED` escrow.
3.  **Action**: Try to click "Confirm Funds".
4.  **Verify**: Backend returns `403 Forbidden` (`CUSTODIAN` required).

---

## 🔒 Scenario 4: Security Validation ("No Free Money")
**Goal**: Verify the "No Free Money" patch persists even with authorized users.

1.  **Login** as **Agent (Alice)** -> Create New Escrow.
2.  **Logout**.
3.  **Login** as **Contractor (Bob)** -> Upload Evidence.
4.  **Logout**.
5.  **Login** as **Inspector (Jim)**.
    *   *Context*: Escrow is `CREATED` (Not Funded).
6.  **Action**: Click **"Approve Release"**.
7.  **Verify Result**:
    *   **UI**: Red Error Banner appears: **"Security Alert: Cannot approve release. Escrow validation failed (Not Funded)."**
    *   **State**: Remains `CREATED`. Money is safe.

---

## 📝 Test Data Summary

| Role | Username | Password | Permission |
| :--- | :--- | :--- | :--- |
| **Agent** | `alice_agent` | `password123` | Create Only |
| **Contractor** | `bob_contractor` | `password123` | Upload Only |
| **Inspector** | `jim_inspector` | `password123` | Approve Only |
| **Custodian** | `title_co` | `password123` | Fund Only |

---

## 🔄 Scenario 5: Budget / Funding Change Order
**Goal**: Verify the "Append-Only" Budget Increase logic. Ensure that adding funds DOES NOT reset the escrow state and simply adds new milestones awaiting "Delta Funding".

### Setup
You may continue with the Escrow from **Scenario 1** (Status: `FUNDED` or Partially Paid).
1.  **Login**: As **Agent (Alice)**.
2.  **Navigate**: To the Active Escrow.

### Step 1: Initiate Budget Change
1.  **Action**: Click the **"Change Budget / Funding"** button (Black button).
2.  **Verify UI Modal**:
    *   Title: **"Increase Project Budget"**.
    *   Warning: "You are adding new funds to the project."
    *   Note: "New funds will remain locked until re-confirmed by the Client".
3.  **Input**: Enter an amount (e.g., `15000`).
4.  **Confirm**: Click **"Add New Funding"**.

### Step 2: Verify Initial Effect (No Reset)
1.  **Verify UI**:
    *   **Escrow State**: Remains **`FUNDED`** (Active). It generally does *not* revert to `CREATED`.
    *   **Funding Status**: Shows **"Partial Funding"** warning badge.
    *   **New Milestone**: Appears at the bottom (e.g., "Change Order – Electrical Upgrade").
    *   **Milestone Badge**: Shows **"Waiting for Funding"** (Status: `CREATED`).
    *   **Existing Milestones**: Previous statuses (`PAID`, `PENDING`) remain untouched.

### Step 3: Confirm Delta Funds (Custodian)
1.  **Logout** Alice -> **Login** as **Custodian (TitleCo)**.
2.  Navigate to the Escrow.
3.  **Action**: Click **"Confirm Funds"**. (This confirms the *delta* amount).
4.  **Verify Outcome**:
    *   **Funding Status**: "Partial Funding" warning disappears.
    *   **New Milestone**: Status changes from "Waiting for Funding" to **`PENDING`** (Ready for work).
    *   **Audit Log**: A `CHANGE_ORDER_ADDED` event is recorded.

### Step 4: Immutability Check
1.  **Verify**: Paid milestones cannot be modified or deleted. The system is "Append-Only".
