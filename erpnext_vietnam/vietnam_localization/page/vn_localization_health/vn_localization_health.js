frappe.pages["vn-localization-health"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Vietnam Localization Health"), single_column: true });
	const body = $('<div class="p-4"></div>').appendTo(page.body);
	const company = page.add_field({
		fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1,
		default: frappe.defaults.get_user_default("Company"), change: () => refresh_health(),
	});
	page.add_button(__("Open Setup"), () => frappe.set_route("vn-setup-wizard"));
	page.set_primary_action(__("Refresh"), () => refresh_health());

	function badge(value) {
		const map = { READY: "green", READY_WITH_WARNINGS: "orange", NEEDS_ATTENTION: "red", NOT_CONFIGURED: "gray" };
		return `<span class="indicator-pill ${map[value] || "gray"}">${frappe.utils.escape_html(value || "-")}</span>`;
	}
	function yesno(value) { return value ? __("Yes") : __("No"); }
	function render(result) {
		const setup = result.setup || {};
		const counts = result.counts || {};
		const warnings = result.warnings || [];
		const warning_html = warnings.length ? warnings.map((w) =>
			`<div class="alert ${w.level === "ERROR" ? "alert-danger" : "alert-warning"} py-2 mb-2"><b>${frappe.utils.escape_html(w.code)}</b> — ${frappe.utils.escape_html(w.message)}</div>`
		).join("") : `<div class="alert alert-success py-2">${__("No operational warnings detected.")}</div>`;
		body.html(`
			<div class="frappe-card p-4 mb-3"><div class="d-flex justify-content-between align-items-center"><h4 class="m-0">${frappe.utils.escape_html(result.company || "")}</h4>${badge(result.overall_status)}</div></div>
			<div class="row">
				<div class="col-md-6"><div class="frappe-card p-4 mb-3"><h5>${__("Setup")}</h5><p>${__("Business Profile")}: <b>${frappe.utils.escape_html(setup.business_profile || "-")}</b><br>${__("Accounting Regime")}: <b>${frappe.utils.escape_html(setup.accounting_regime || "-")}</b><br>${__("VAT Method")}: <b>${frappe.utils.escape_html(setup.vat_method || "-")}</b><br>${__("Snapshot")}: <code>${frappe.utils.escape_html((setup.setup_snapshot_hash || "-").slice(0, 16))}</code></p></div></div>
				<div class="col-md-6"><div class="frappe-card p-4 mb-3"><h5>${__("Features")}</h5><p>${__("HRMS installed")}: <b>${yesno(result.hrms_installed)}</b><br>${__("PIT Payroll")}: <b>${yesno(setup.enable_payroll_compliance)}</b><br>${__("Social Insurance")}: <b>${yesno(setup.enable_social_insurance)}</b><br>${__("E-Invoice Preparation")}: <b>${yesno(setup.enable_einvoice)}</b><br>${__("Compliance Gateway")}: <b>${yesno(setup.enable_compliance_gateway)}</b></p></div></div>
				<div class="col-md-12"><div class="frappe-card p-4 mb-3"><h5>${__("Operational Counts")}</h5><p>${__("COA mappings")}: <b>${counts.coa_mappings || 0}</b> · ${__("E-Invoice profiles")}: <b>${counts.einvoice_profiles || 0}</b> · ${__("Enabled endpoints")}: <b>${counts.enabled_integration_endpoints || 0}</b> · ${__("Tax declarations")}: <b>${counts.tax_declarations || 0}</b> · ${__("BHXH exports")}: <b>${counts.social_insurance_exports || 0}</b> · ${__("E-Invoices")}: <b>${counts.einvoices || 0}</b> · ${__("Submissions")}: <b>${counts.submissions || 0}</b></p></div></div>
				<div class="col-md-12"><div class="frappe-card p-4"><h5>${__("Warnings")}</h5>${warning_html}<p class="text-muted mb-0">${__("This page reports operational readiness only; it is not a legal or tax-compliance certification.")}</p></div></div>
			</div>`);
	}
	function refresh_health() {
		const value = company.get_value();
		if (!value) return;
		frappe.call({ method: "erpnext_vietnam.diagnostics.health.get_health", args: { company: value }, freeze: true,
			callback: (r) => render(r.message || {}) });
	}
	if (company.get_value()) refresh_health();
};
