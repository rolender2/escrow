# User Acceptance Testing (UAT) Guide
**Project**: Programable Escrow Automation Platform (MVP)
**Version**: 2.1 (Full Feature Set)

This guide is designed as a **Single Continuous Story** ("The HVAC Installation Project"). By following these scenarios in order, you will verify every feature of the platform, from simple creation to complex dispute resolution and notifications.

---

## 🏗️ Prerequisites
*   **Backend**: `http://localhost:8000` (Running)
*   **Frontend**: `http://localhost:3000` (Running)
*   **Users**: Seeded via `verify_notifications.py` or manually.

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Agent** | `alice_agent` | `password123` | Orchestrates the Deal |
| **Custodian** | `title_co` | `password123` | Controls the Money (Gatekeeper) |
| **Contractor** | `rick_contractor` | `password123` | Does the Work & Uploads Proof |
| **Inspector** | `rob_inspector` | `password123` | Verifies Work & Approves Pay |

---

## 🎬 Scenario 1: The Foundation (Happy Path)
**Goal**: Establish trust. Create a secure agreement, fund it, and verify the Notification System acts as the project's heartbeat.

### Step 1: Agent Creates the Agreement
1.  **Login** as **Agent (Alice)**.
2.  **Action**: Click **"+ New Project Escrow"**.
3.  **Input**:
    *   **Buyer**: `Alice Buyer`
    *   **Provider**: `Hanks HVAC`
    *   **Amount**: `10,000`
    *   **Milestone**: `New HVAC` ($10,000)
4.  **Click**: **"Create & Lock Funds"**.
5.  **Verify**:
    *   Escrow State: **`CREATED`** (Amber Badge).
    *   **Milestone**: Single entry for $10,000.
    *   **Notification Bell**: Check the bell icon (top right). You should see an entry: *"Escrow Created: Waiting for Custodian Confirmation."*

### Step 2: Custodian Locks the Funds
1.  **Login** as **Custodian (TitleCo)**.
    *   *Check Notification*: Bell should show **1** unread. Dropdown: *"New Escrow Created. Waiting for Custodian Confirmation."*
2.  **Action**: Click the Notification (marks as read).
3.  **Action**: Navigate to the Escrow (if not already there).
4.  **Action**: Click **"(Simulate) Confirm Funds"** (Amber Button).
4.  **Verify**:
    *   Escrow State: **`FUNDED`** (Blue Badge).
    *   Milestone Status: **`PENDING`** (Ready for work).

### Step 3: Notification Check (Agent)
1.  **Login** as **Agent (Alice)**.
2.  **Verify**: Notification received: *"Funds have been confirmed by Custodian."*
3.  **Action**: Click **"Mark as Read"** in the dropdown. The badge count decreases.


---

## 🔄 Scenario 2: The Change Order (Agreement Versioning)
**Goal**: The scope changes. Verify "Append-Only" Budget logic. We need more funds for an **"Electrical Upgrade"**.

### Step 1: Agent Initiates Change
1.  **Login** as **Agent (Alice)**.
2.  **Action**: Click **"Change Budget / Funding"** (Black Button).
3.  **Review Modal**:
    *   *Title*: "Increase Project Budget".
    *   *Note*: "New funds will remain locked until re-confirmed..."
4.  **Click**: **"Add New Funding"**.
5.  **Verify**:
    *   **State**: Remains **`FUNDED`** (Project does not stop).
    *   **Badge**: A "Partial Funding" warning appears (Amber).
    *   **Milestones**: A new 2nd Milestone appears: *"Change Order – Electrical Upgrade"* (Status: `CREATED`).
    *   **Amount**: New milestone is for **$15,000**.

### Step 2: Custodian Confirms "Delta"
1.  **Login** as **Custodian (TitleCo)**.
2.  **Action**: Click **"(Simulate) Confirm Funds"** (Amber Button). (This confirms ONLY the new $15,000).
3.  **Verify**:
    *   "Partial Funding" warning disappears.
    *   New Milestone becomes **`PENDING`**.
    *   **Total Locked Value**: Now shows `$25,000`.

---

## 🛑 Scenario 3: The Dispute (Safety Valve)
**Goal**: A disagreement occurs. Verify the "Freeze, Do Not Decide" mechanism blocks money movement.

### Step 1: Raise Dispute (Agent)
1.  **Login** as **Agent (Alice)**.
2.  **Action**: On "New HVAC", click **"Raise Dispute"**.
3.  **Verify**:
    *   Milestone Badge: **`DISPUTED`** (Red/Pulsing).
    *   **Notification**: Inspector receives alert: *"A Dispute has been raised on this escrow."*.


### Step 2: Verify Hard Lock (Inspector)
1.  **Login** as **Inspector (Rob)**.
2.  **Navigate** to the Escrow.
3.  **Attempt**: Look for "Approve Release" on "New HVAC".
    *   **Result**: Button is **HIDDEN**. Money cannot move while disputed.

### Step 3: Resolve (Resume)
1.  **Action**: As Inspector (or Agent), click **"Resume Milestone"** on "New HVAC".
2.  **Verify**: Status returns to **`PENDING`**. Operations normalize.

---

## 📎 Scenario 4: External Verification (New Feature)
**Goal**: The City Inspector sends a permit. Verify "External Evidence" does not trigger payment.

### Step 1: Inspector Attaches Permit
1.  **Login** as **Inspector (Jim)**.
2.  **Action**: Click **"+ Attach External Evidence"** (Green text).
3.  **Input**:
    *   Type: `PDF`.
    *   File: Select any dummy test file.
4.  **Confirm**: Click **"Attach Evidence"**.
5.  **Verify**:
    *   New Item: "External Attestation" (PDF Icon).
    *   **Badge**: **"EXTERNAL"** (Distinct Purple Color).
    *   **State check**: Milestone is still `PENDING`. Payment **NOT** released.

---

## ✅ Scenario 5: Completion (Formal Handoff)
**Goal**: Contractor finishes work. Verify the formal "Submission" workflow and final payout.

### Step 1: Contractor Submission
1.  **Login** as **Contractor (Rick)**.
2.  **Action (Upload)**:
    *   Select Source: `Photo`.
    *   Upload functionality: Select file -> **"Upload"**.
3.  **Action (Finalize)**:
    *   Click **"Finish Submission"** (Green Button).
    *   **Confirm**: "I attest this work is complete..."
4.  **Verify**:
    *   Status: **`EVIDENCE_SUBMITTED`**.
    *   Buttons: Locked. Contractor cannot upload more or retract.

### Step 2: Inspector Approves
1.  **Login** as **Inspector (Rob)**.
    *   *Check Notification*: *"New Evidence submitted. pending inspection."*
2.  **Action**: Click **"Approve Release"**.

3.  **Verify**:
    *   Status: **`PAID`** (Green).
    *   **Ledger**: Records `PAYMENT_RELEASED`.

---

## 💸 Scenario 6: The Payment Instruction (Ledger Backed)
**Goal**: Verify the "No Money Moves Without Instruction" rule. The system simulates banking instructions.

### Step 1: Verify Instruction Generation (Agent)
1.  **Login** as **Agent (Alice)**.
2.  **Navigate** to the Escrow Detail.
3.  **Scroll Down** to "Payment Instructions" (New Section).
4.  **Verify**:
    *   **Entry**: Simulating the $10,000 payout for "New HVAC".
    *   **Status**: **`INSTRUCTED`** (Blue Badge).
    *   **Actions**: No buttons visible (Agent is Read-Only).

### Step 2: Custodian Processing
1.  **Login** as **Custodian (TitleCo)**.
2.  **Action**: Locate the Payment Instruction.
3.  **Click**: **"Mark Sent"** (Purple Button).
    *   **Verify**: Status changes to **`SENT`**.
4.  **Click**: **"Confirm Settlement"** (Green Button).
    *   **Verify**: Status changes to **`SETTLED`**.

### Step 3: Notification Check
1.  **Login** as **Agent (Alice)**.
2.  **Verify**: Notifications received for *"Payment instruction sent to banking system."* and *"Funds have been released and settled."*.


---

## 📜 Scenario 7: The Audit Trail

**Goal**: Verify the "Tamper-Evident" promise.

1.  **Login** as **Agent (Alice)**.
2.  **Action**: Click **"View Ledger"**.
3.  **Verify Chain**:
    *   Scroll to bottom.
    *   Check that **Entry 1** (`CREATE`) is linked to **Entry 2** (`CONFIRM`), which is linked to **Entry 3** (`CHANGE_ORDER`), etc.
    *   **Notifications**: Ensure `NOTIFICATION_ISSUED` events appear in the stream, proving communication was also audited.

**End of Testing**
