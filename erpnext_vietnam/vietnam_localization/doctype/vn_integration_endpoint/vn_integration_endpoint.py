import json
import frappe
from frappe.model.document import Document

class VNIntegrationEndpoint(Document):
	def validate(self):
		if self.environment == "PRODUCTION" and self.enabled and not self.credential_reference:
			frappe.throw("Production endpoint requires a credential reference")
		if self.capabilities_json:
			try:
				value = json.loads(self.capabilities_json)
			except json.JSONDecodeError:
				frappe.throw("Capabilities JSON must be valid JSON")
			if not isinstance(value, (list, dict)):
				frappe.throw("Capabilities JSON must be an array or object")
