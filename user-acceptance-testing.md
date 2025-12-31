# User Acceptance Testing (UAT) Guide
**Project**: Programable Escrow Automation Platform (MVP)
**Version**: 1.0 (Audit-Grade)

This guide provides step-by-step scenarios to verify the functionality of the Escrow Platform. Use the specific **Test Data** provided to ensure consistent results.

---

## 🏗️ Prerequisites
*   **Backend**: Running on `http://localhost:8000` (FastAPI + MongoDB Ledger)
*   **Frontend**: Running on `http://localhost:3000` (Next.js)
*   **Database**: Reset to clean state (Optional but recommended).

---

## 🧪 Scenario 1: The "Happy Path" (Create to Payout)
**Goal**: Verify the standard lifecycle of a repair escrow with strict custody checks.

### Step 1: Real Estate Agent Creates Agreement
1.  Navigate to **Dashboard** (`http://localhost:3000`).
2.  Click **"+ New Repair Escrow"**.
3.  **Enter Test Data**:
4.  **Enter Test Data**:
    *   **Buyer (Client)**: `Alice Buyer`
    *   **Service Provider (Contractor)**: `Robs Roof`
    *   **Amount ($)**: `5000`
    *   **Repair Item**: `Roof Repair - North Wing`
    *   **Evidence Type**: (Hidden/Auto-set to `Photo`)
5.  Click **"Create & Lock Funds"**.
5.  **Verify**:
    *   You are redirected to the Dashboard.
    *   New Item appears with State: **`CREATED`** (Amber Badge).
    *   *Note*: Funds are NOT active. Work cannot begin.

### Step 2: Custodian Confirms Funds (The "Gap")
1.  Click on the newly created Escrow (ID starting with `...`).
2.  Observe standard warning: **"⚠ Funds NOT Confirmed"**.
3.  Click the button: **"(Simulate) Confirm Wire Received"**.
    *   *Context*: In the real world, this button is only available to the Title Company after checking their bank account.
4.  **Verify**:
    *   Page refreshes.
    *   State changes to **`FUNDED`** (Blue Badge).
    *   Status is now `PENDING` (Ready for work).

### Step 3: Contractor Uploads Evidence
1.  Scroll to "Milestones".
2.  Locate "Roof Repair - North Wing".
3.  **Enter Test Data**:
    *   **Evidence Type**: Select `Photo`
    *   **URL**: `https://s3.cloud/evidence/roof_completed.jpg`
4.  Click **"Upload"**.
5.  **Verify**:
    *   Milestone Status changes to **`EVIDENCE_SUBMITTED`**.
    *   "Approve Release" button becomes enabled (previously disabled).

### Step 4: Inspector Approves Release
1.  Act as the Inspector.
2.  Review the Evidence URL.
3.  Click **"Approve Release"**.
4.  **Verify**:
    *   Milestone Status changes to **`PAID`** (Green).
    *   **Success!** The logic has generated the Banking Instruction.

---

## 🕵️ Scenario 2: Immutable Audit Trail
**Goal**: Verify that the system captured a cryptographically linked history of Scenario 1.

1.  Navigate to **Dashboard** -> Click **"View Ledger"** (Top right).
2.  **Verify the Chain** (Read from bottom to top):
    *   **Entry 1 (Genesis)**:
        *   Event: `CREATE`
        *   Data: Contains `Alice_Buyer_001` / `Bobs_Roofing_LLC`.
        *   `Previous Hash`: (Lots of zeros).
    *   **Entry 2**:
        *   Event: `CONFIRM_FUNDS`
        *   Actor: `TitleCompany_X` (The simulated custodian).
        *   `Previous Hash`: Matches `Current Hash` of Entry 1.
    *   **Entry 3**:
        *   Event: `UPLOAD_EVIDENCE`
        *   Actor: `CONTRACTOR_API`.
    *   **Entry 4 (Latest)**:
        *   Event: `APPROVE`
        *   Actor: `INSPECTOR_ID`.
3.  **Pass Criteria**: The `Previous Hash` of every entry strictly matches the `Current Hash` of the one below it.

---

## 🛡️ Scenario 3: Role Enforcement (Negative Testing)
**Goal**: Verify safety rules prevent illegal actions.

### Test A: Approve Without Evidence
1.  Create a new Escrow (Buyer: `Test_Fail_User`, Amount: `100`).
2.  Confirm Funds.
3.  **Do NOT** upload evidence.
4.  Try to click **"Approve Release"**.
5.  **Verify**: The button is **Disabled** (Greyed out). The system physically prevents approval without proof.

### Test B: Fund Without Custodian
*   *Note*: This is a backend API test. The UI hides the button for non-created states, but logically, funds cannot move from `CREATED` to `ACTIVE` without the specific `CONFIRM_FUNDS` event trigger.

---

## 📝 Test Data Summary

| Field | Value | Purpose |
| :--- | :--- | :--- |
| **Buyer** | `Alice_Buyer_001` | Standard Customer |
| **Provider** | `Bobs_Roofing_LLC` | Standard Contractor |
| **Amount** | `5000.00` | Repair Cost |
| **Custodian** | `TitleCompany_X` | Role: Title Officer |
| **Confirm Code**| `WIRE_123` | Wire Reference ID |
| **Inspector** | `Inspector_Jim` | Role: Approver |

---

## 🔒 Security & Authority Model (Gap Analysis D)
> **Principle**: No single actor can control the lifecycle. Authority is enforced server-side.

1.  **Segregation of Duties**:
    *   **Agents**: Can CREATE agreements but CANNOT approve releases.
    *   **Contractors**: Can UPLOAD evidence but CANNOT approve releases.
    *   **Inspectors**: Can APPROVE releases but CANNOT create agreements.
    *   **Custodians**: Can CONFIRM FUNDS (activates the deal) but CANNOT modify terms.
2.  **Immutability**:
    *   Once `FUNDED`, terms are hashed and locked.
    *   Edits require a **New Agreement Version**.

---

## 📜 Agreement Lifecycle & Versioning (Gap Analysis A)
*   **CREATED**: Mutable. Terms can be negotiated.
*   **FUNDED**: Immutable. Agreement Hash is finalized.
*   **ACTIVE**: Work in progress.
*   **DISPUTED**: Locked. No funds can move.
*   **PAID**: Terminal state.

> **Note**: Change Orders currently require creating a new Agreement (v2) linked to the previous hash.

---

## 📄 Formal Banking Instruction Schema (Gap Analysis B)
Upon approval, the system generates a legally binding JSON artifact. Compare this against your banking requirements:

```json
{
  "instruction_id": "UUID-...",
  "agreement_id": "ESCROW-...",
  "agreement_version": "v1",
  "agreement_hash": "sha256:...",
  "payee": "Bobs_Roofing_LLC",
  "amount": 5000.00,
  "currency": "USD",
  "approvals": [
    {
      "approver": "Inspector_Jim",
      "signature": "simulated_sig_...",
      "timestamp": "2025-..."
    }
  ],
  "attestation": "All conditions defined in Agreement v1 have been satisfied."
}
```

---

## 💥 Scenario 4: Failure & Edge Conditions (Gap Analysis C & E)

### Test A: The "Dispute" Halt
**Goal**: Verify that a dispute freezes the funds.
1.  **Trigger**: Send `POST /escrows/{id}/dispute` (simulating a "Raise Dispute" button click).
2.  **Verify State**: Escrow State becomes **`DISPUTED`**.
3.  **Attempt Release**: Try to Approve/Release funds.
4.  **Result**: ❌ **Error 400: Escrow is HALTED or DISPUTED.** (Funds are safe).

### Test B: Duplicate Approval (Idempotency)
1.  Click "Approve Release" on an already PAID milestone.
2.  **Result**: System ignores the request or returns current state. State remains `PAID`. Money is not sent twice.

### Test C: Missing Evidence
1.  Try to Approve a milestone with Status `PENDING` (No evidence).
2.  **Result**: ❌ **Error 400: Missing Evidence.**

