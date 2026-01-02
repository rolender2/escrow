# VeriDraw: Construction Trust Protocol

VeriDraw is a specialized escrow automation platform designed for high-trust construction payments. It replaces "trust me" with **"Rule-Enforced Fund Control"**.

## Core Philosophy

1.  **Tamper-Evident Audit Trail**: Every action (Creation, Funding, Approval) is cryptographically hashed and linked to the previous event, creating an unbreakable chain of custody.
2.  **Role-Based Fund Control**: System rules prevent unauthorized actions. Agents create, Custodians fund, Contractors work, and Inspectors approve. No single actor can move funds alone.
3.  **Append-Only Budget Changes**:
    *   **Immutability**: Once created, milestones and agreements are permanent.
    *   **Delta Funding**: Budget increases create *new* milestones. The original agreement remains active, and new funds are confirmed separately (Delta Funding) without resetting the main escrow state.
4.  **Safety, Not Judgment**: The system includes a **Dispute & Exception Handling** layer ("Freeze, Do Not Decide"). Authorized parties can pause (Dispute) fund releases, blocking all actions until resolved or cancelled, without reversing prior ledger entries.

## Features

- **Smart Escrows**: Logic-driven agreements that hold funds until specific conditions (uploaded evidence + inspector signature) are met.
- **Strict Role Enforcement**:
    - `AGENT`: Creates Agreements, Initiates Change Orders.
    - `CUSTODIAN`: Confirms Funds (The Gatekeeper).
    - `CONTRACTOR`: Uploads Evidence (Photos/Invoices).
    - `INSPECTOR`: Approves Releases (The Key).
- **Agreement Integrity**:
    - "New Money = New Authority": Increasing the budget requires explicit confirmation of the additional funds.
    - **No State Resets**: Existing approved work continues uninterrupted during budget upgrades.
    - **No State Resets**: Existing approved work continues uninterrupted during budget upgrades.
    - **Change Orders**: strictly additive (Append-Only). Retroactive changes are forbidden.
- **Dispute & Exception Handling**:
    - **"Freeze, Do Not Decide"**: Disputes pause a milestone but do not judge it.
    - **Hard Blocks**: Disputed milestones block all Approval and Evidence Upload actions.
    - **Fail Safe**: Milestones can be Resumed (restoring state) or Cancelled (permanently locked, with confirmation).

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Testing
See `user-acceptance-testing.md` for detailed manual verification scenarios.
Run `python backend/verify_change_orders.py` for automated testing of the Budget Change logic.
