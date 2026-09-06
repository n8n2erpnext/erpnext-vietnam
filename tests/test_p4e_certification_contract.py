import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ORCH=(ROOT/"erpnext_vietnam/integration/orchestrator.py").read_text()
ENDPOINT=(ROOT/"erpnext_vietnam/vietnam_localization/doctype/vn_integration_endpoint/vn_integration_endpoint.py").read_text()
UAT=(ROOT/"erpnext_vietnam/integration/certification_uat.py").read_text()


class TestP4ECertificationContract(unittest.TestCase):
    def test_runtime_requires_current_production_certification_pin(self):
        self.assertIn("require_production_certification", ORCH)
        self.assertIn("certification pin is missing or stale", ORCH)
        self.assertIn("adapter_certification_hash", ORCH)

    def test_endpoint_pins_certification_on_reviewed_save(self):
        self.assertIn("require_production_certification", ENDPOINT)
        self.assertIn("adapter_certification_version", ENDPOINT)
        self.assertIn("adapter_certification_hash", ENDPOINT)
        schema=json.loads((ROOT/"erpnext_vietnam/vietnam_localization/doctype/vn_integration_endpoint/vn_integration_endpoint.json").read_text())
        fields={f["fieldname"] for f in schema["fields"]}
        self.assertTrue({"adapter_certification_version","adapter_certification_hash"} <= fields)

    def test_live_uat_is_transport_free_and_rollback_only(self):
        self.assertIn("uncertified_blocked", UAT)
        self.assertIn("certification_hash", UAT)
        self.assertIn("frappe.db.rollback()", UAT)
        self.assertNotIn("frappe.db.commit()", UAT)
        self.assertIn("must never transport", UAT)


if __name__ == "__main__": unittest.main()
