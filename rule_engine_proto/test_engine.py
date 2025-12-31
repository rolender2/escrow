import unittest
from engine import EscrowAgreement, EscrowState, MilestoneStatus

class TestEscrowEngine(unittest.TestCase):
    def setUp(self):
        self.escrow = EscrowAgreement("buyer", "provider", 1000.0)
        self.escrow.add_milestone("Test Milestone", 1000.0, ["Photo"])
        self.escrow.deposit_funds(1000.0)
        self.escrow.start_project()

    def test_milestone_flow(self):
        """Test the happy path: Evidence -> Approval -> Release"""
        ms = self.escrow.milestones[0]
        
        # 1. Evidence
        ms.add_evidence("Photo", "http://url")
        self.assertEqual(ms.status, MilestoneStatus.EVIDENCE_SUBMITTED)
        
        # 2. Approve
        ms.approve("approver", "sig")
        self.assertEqual(ms.status, MilestoneStatus.APPROVED)
        
        # 3. Release
        instruction = self.escrow.generate_release_instruction(0)
        self.assertIsNotNone(instruction)
        self.assertEqual(instruction["amount"], 1000.0)
        self.assertEqual(ms.status, MilestoneStatus.PAID)
        self.assertEqual(self.escrow.state, EscrowState.COMPLETED)

    def test_missing_evidence(self):
        """Test validation preventing approval without required evidence"""
        ms = self.escrow.milestones[0]
        # Try to approve without adding "Photo"
        with self.assertRaises(ValueError) as cm:
             ms.approve("approver", "sig")
        self.assertIn("Missing evidence", str(cm.exception))

    def test_early_release_attempt(self):
        """Test validation preventing release before approval"""
        ms = self.escrow.milestones[0]
        ms.add_evidence("Photo", "http://url")
        # Status is EVIDENCE_SUBMITTED, not APPROVED
        with self.assertRaises(ValueError) as cm:
            self.escrow.generate_release_instruction(0)
        self.assertIn("not approved", str(cm.exception))

    def test_over_allocation(self):
        """Test that milestones cannot exceed total budget"""
        e = EscrowAgreement("b", "p", 100.0)
        with self.assertRaises(ValueError):
            e.add_milestone("Too Big", 101.0, [])

if __name__ == '__main__':
    unittest.main()
