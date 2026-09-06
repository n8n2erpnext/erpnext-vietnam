import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCH = (ROOT / "erpnext_vietnam/integration/orchestrator.py").read_text()
GATEWAY = (ROOT / "erpnext_vietnam/einvoice/gateway.py").read_text()
EINV_PY = (ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_e_invoice/vn_e_invoice.py").read_text()
SUB_PY = (ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_submission/vn_submission.py").read_text()


class TestP4DArchiveContract(unittest.TestCase):
    def test_gateway_persists_private_provider_neutral_evidence(self):
        self.assertIn("def _persist_acceptance_evidence", ORCH)
        self.assertIn("is_private=1", ORCH)
        self.assertIn("acceptance_evidence_hash", ORCH)
        self.assertNotIn("requests.", ORCH)

    def test_einvoice_archive_chains_source_submission_and_evidence_hashes(self):
        self.assertIn('"VN-EINVOICE-ARCHIVE-2026-01"', GATEWAY)
        self.assertIn('"canonical_payload_hash"', GATEWAY)
        self.assertIn('"submission_payload_hash"', GATEWAY)
        self.assertIn('"acceptance_evidence_hash"', GATEWAY)
        self.assertIn("final_xml_sha256", GATEWAY)

    def test_archive_fields_are_immutable_after_acceptance(self):
        self.assertIn("ACCEPTANCE_ARCHIVE_FIELDS", EINV_PY)
        self.assertIn("Accepted e-invoice archive evidence is immutable", EINV_PY)
        self.assertIn("ACCEPTANCE_ARCHIVE_FIELDS", SUB_PY)
        self.assertIn("Accepted submission archive evidence is immutable", SUB_PY)

    def test_schema_contains_archive_fields(self):
        einv = json.loads((ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_e_invoice/vn_e_invoice.json").read_text())
        sub = json.loads((ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_submission/vn_submission.json").read_text())
        ef = {f["fieldname"] for f in einv["fields"]}
        sf = {f["fieldname"] for f in sub["fields"]}
        self.assertTrue({"archive_snapshot_json", "archive_snapshot_hash", "archive_locked_at"} <= ef)
        self.assertTrue({"acceptance_evidence_json", "acceptance_evidence_hash", "acceptance_recorded_at"} <= sf)


if __name__ == "__main__":
    unittest.main()
