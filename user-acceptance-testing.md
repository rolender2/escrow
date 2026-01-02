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
3.  Click **"+ New Project Escrow"**.
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
3.  **Action - Upload**:
    *   In the "Roof Repair" milestone, look for the **"Required Items"** section.
    *   Select **Source Type** (e.g., "Photo").
    *   Click **"Choose File"** and select a test image/PDF.
    *   Click **"Upload"**.
    *   *Optional*: Repeat to add a second file (e.g., an Invoice PDF).
4.  **Action - Submit**:
    *   Click the green **"Finish Submission"** button.
    *   **Confirm Modal**: Read the attestation warning and click **"Confirm Submission"**.
5.  **Verify**:
    *   Milestone Status changes to **`EVIDENCE_SUBMITTED`**.
    *   The "Finish Submission" button changes to a disabled **"Submission Complete"** badge.
    *   "Approve Release" button becomes visible/enabled for the Inspector (Bob cannot see it).
6.  **Logout**.

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

---

## 🛑 Scenario 6: Dispute Resolution & Safety Valves
**Goal**: Verify the "Freeze, Do Not Decide" safety mechanism. Authorized parties can block funds by raising a Dispute, preventing any further action until resolved.

### Setup
You can **continue from Scenario 5** (using the new "Change Order" milestone which is `PENDING`) OR create a **New Project Escrow**.
*   **Target**: Any milestone with status `PENDING` or `EVIDENCE_SUBMITTED`.

### Step 1: Raise a Dispute (Agent)
1.  **Login** as **Agent (Alice)**.
2.  Find a milestone with status **`PENDING`** or **`EVIDENCE_SUBMITTED`**.
3.  **Action**: Click the **"Raise Dispute"** button (small red text).
    *   *Note*: If not visible, ensure you are not logged in as the Contractor.
4.  **Verify UI**:
    *   **Badge**: Status changes to **`DISPUTED`** (Red/Pulsing).
    *   **Controls**: "Raise Dispute" is replaced by **"Resume Milestone"** (Green) and **"Cancel Milestone"** (Red).
5.  **Logout**.

### Step 2: Verify Enforcement (Hard Blocks)
1.  **Login** as **Inspector (Jim)**.
2.  Navigate to the Disputed Milestone.
3.  **Action**: Check for the **"Approve Release"** button.
4.  **Verify**:
    *   **"Approve Release"** is **HIDDEN** (Correct: Cannot approve disparate milestone).
    *   **"Resume / Cancel"** buttons are **VISIBLE** (Inspectors are trusted to resolve).
    *   *Result*: Action is effectively blocked by removal of the control.
5.  **Logout**.

### Step 3: Resume Milestone
1.  **Login** as **Agent (Alice)** (or Inspector/Custodian).
2.  Navigate to the Disputed Milestone.
3.  **Action**: Click **"Resume Milestone"**.
4.  **Verify**:
    *   Badge returns to its previous state (e.g., **`PENDING`** or **`EVIDENCE_SUBMITTED`**).
    *   "Raise Dispute" link reappears.
    *   Actions (Upload/Approve) are unblocked.

### Step 4: Cancel Milestone (Permanent Lock)
1.  **Action**: Raise Dispute again.
2.  **Action**: Click **"Cancel Milestone"**.
3.  **Verify UI Modal**:
    *   **Warning**: "This action is irreversible."
    *   **Consequences**: Funds remain locked.
4.  **Action**: Click **"Confirm Cancellation"** (Red Button).
5.  **Verify**:
    *   Badge changes to **`CANCELLED`**.
    *   No further actions are available. The milestone is effectively dead.

### Step 5: Negative Test (Contractor)
1.  **Login** as **Contractor (Bob)**.
2.  Navigate to a Pending/Active milestone.
3.  **Verify**: The **"Raise Dispute"** button is **NOT VISIBLE**.
4.  **Action (Advanced)**: Attempt to call the API manually via curl/Postman.
5.  **Verify**: Backend returns `403 Forbidden` ("Contractors cannot raise disputes").

---

## 📎 Scenario 7: External Evidence Attestation
**Goal**: Verify that authorized third parties (Inspector, Agent) can attach evidence without triggering payment, and that Contractors are blocked.

### Setup
*   **Target**: Any milestone with status `PENDING` or `EVIDENCE_SUBMITTED`.

### Step 1: Inspector Attaches Evidence
1.  **Login** as **Inspector (Jim)**.
2.  Navigate to a Pending Milestone.
3.  **Action**: Click **"+ Attach External Evidence"**.
4.  **Verify UI Modal**:
    *   Title: **"Attach External Evidence"**.
    *   Warning: "This does not approve payment."
5.  **Input**:
    *   Evidence Type: `PDF` or `PHOTO`.
    *   File: Select a test file (e.g., a dummy PDF or Image).
6.  **Action**: Click **"Attach Evidence"**.
7.  **Verify**:
    *   A new Evidence item appears in the list.
    *   **Badge**: Shows **"EXTERNAL"** (Purple Badge).
    *   **Status check**: The Milestone status remains unchanged (e.g., `PENDING`). Payment is NOT released.

### Step 2: Contractor Blocked
1.  **Logout** and **Login** as **Contractor (Bob)**.
2.  Navigate to the same milestone.
3.  **Verify**:
    *   The **"+ Attach External Evidence"** button is **NOT VISIBLE**.
    *   The Contractor sees the Inspector's uploaded evidence with the "EXTERNAL" badge.
    *   The Contractor CANNOT delete or modify it.

### Step 3: Audit Trail Verification
1.  **Login** as **Agent (Alice)** -> View Ledger.
2.  **Verify**:
    *   A new Event `EVIDENCE_ATTESTED` is recorded.
    *   Actor: `jim_inspector`.
    *   Role: `INSPECTOR`.
