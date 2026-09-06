import json

import frappe
from frappe.model.document import Document


class VNIntegrationEndpoint(Document):
    def validate(self):
        if self.timeout_seconds is not None and int(self.timeout_seconds) < 1:
            frappe.throw("Timeout Seconds must be at least 1")
        if self.environment == "PRODUCTION" and self.adapter.startswith("sandbox."):
            frappe.throw("Sandbox adapters cannot be configured as PRODUCTION endpoints")
        if self.environment == "PRODUCTION" and self.enabled and not self.credential_reference:
            frappe.throw("Production endpoint requires a credential reference")
        if self.capabilities_json:
            try:
                value = json.loads(self.capabilities_json)
            except json.JSONDecodeError:
                frappe.throw("Capabilities JSON must be valid JSON")
            if not isinstance(value, (list, dict)):
                frappe.throw("Capabilities JSON must be an array or object")
        if self.enabled:
            from erpnext_vietnam.integration.builtin import register_builtin_adapters
            from erpnext_vietnam.integration.registry import get_adapter

            register_builtin_adapters()
            try:
                adapter = get_adapter(self.adapter)
            except ValueError as exc:
                frappe.throw(str(exc))
            if adapter.channel != self.channel:
                frappe.throw("Enabled endpoint channel must match its registered adapter")
