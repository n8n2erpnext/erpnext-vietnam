import hashlib
import json
import frappe
from frappe.model.document import Document

IMMUTABLE_AFTER_TRANSPORT = {"company", "submission_type", "endpoint", "source_doctype", "source_name", "rule_set", "rule_snapshot_hash", "schema_version", "payload_json", "payload_hash", "idempotency_key"}

class VNSubmission(Document):
	def validate(self):
		try:
			payload = json.loads(self.payload_json)
		except json.JSONDecodeError:
			frappe.throw("Canonical Payload JSON must be valid JSON")
		canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
		self.payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
		identity = "|".join([self.company or "", self.submission_type or "", self.endpoint or "", self.schema_version or "", self.payload_hash])
		self.idempotency_key = hashlib.sha256(identity.encode()).hexdigest()
		if not self.is_new() and self.get_db_value("status") not in (None, "DRAFT", "READY"):
			for field in IMMUTABLE_AFTER_TRANSPORT:
				if self.has_value_changed(field):
					frappe.throw(f"{field} cannot change after transport has started")
