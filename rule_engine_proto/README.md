# Repair Escrow Rule Engine (Prototype)

This is a functional Python prototype for the **"Agent Repair Closer"** platform.
It demonstrates the core logic of a "Rule Engine" that automates the release of funds for Real Estate repair holdbacks.

## Project Structure

*   `engine.py`: The core logic. Contains the `EscrowAgreement` and `Milestone` classes that enforce the rules (Evidence -> Approval -> Release).
*   `demo.py`: A simulated scenario script. It walks through a "Roof Repair" use case where an Agent creates an escrow, a Contractor uploads a photo, an Inspector approves it, and the system generates a banking instruction.
*   `test_engine.py`: Unit tests using Python's standard `unittest` framework to verify edge cases and security logic.

## Prerequisites

*   Python 3.6+

## Quick Start

Run the demonstration scenario to see the workflow in action:

```bash
python3 demo.py
```

### Expected Output
You should see a step-by-step log of the state machine, culminating in a JSON "Banking Instruction":

```json
{
  "instruction_id": "...",
  "action": "RELEASE_FUNDS",
  "amount": 10000.0,
  "reason": "Milestone Completion: Complete Roof Repair",
  ...
}
```

## Running Tests

To verify the logic (e.g., ensuring funds *cannot* be released without approval):

```bash
python3 test_engine.py
```

## Design Notes

This prototype implements a **Non-Custodial** logic model:
1.  **Funds** are assumed to be held by a Title Company or Bank (the "Vault").
2.  **This Software** only generates the *Instruction* to move funds.
3.  **Security**: The `approve()` method requires a digital signature (simulated string) from an authorized `approver_id`.
