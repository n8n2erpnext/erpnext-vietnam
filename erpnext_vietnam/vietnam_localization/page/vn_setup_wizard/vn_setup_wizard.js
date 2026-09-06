frappe.pages["vn-setup-wizard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Vietnam Localization Setup"),
		single_column: true,
	});

	const fields = {};
	const body = $('<div class="frappe-card p-5"></div>').appendTo(page.body);
	$('<p class="text-muted mb-4"></p>')
		.text(__("Choose a business preset and statutory options. Preview is read-only. Government-facing integrations remain disabled until configured separately."))
		.appendTo(body);

	const definitions = [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1 },
		{ fieldname: "business_domain", label: __("Business Domain"), fieldtype: "Select", reqd: 1 },
		{ fieldname: "accounting_regime", label: __("Accounting Regime"), fieldtype: "Select", options: "TT99_2025\nTT133_2016\nCUSTOM_REVIEW_REQUIRED", reqd: 1 },
		{ fieldname: "vat_method", label: __("VAT Method"), fieldtype: "Select", options: "DEDUCTION\nDIRECT\nNOT_CONFIGURED", reqd: 1 },
		{ fieldname: "enable_pit_payroll", label: __("Enable PIT Payroll"), fieldtype: "Check" },
		{ fieldname: "enable_social_insurance", label: __("Enable BHXH/BHYT/BHTN"), fieldtype: "Check" },
		{ fieldname: "enable_einvoice", label: __("Prepare E-Invoice Features"), fieldtype: "Check" },
	];

	definitions.forEach((df) => {
		const control = frappe.ui.form.make_control({ parent: body, df, render_input: true });
		fields[df.fieldname] = control;
	});

	frappe.call({
		method: "erpnext_vietnam.setup.setup_wizard.get_business_domain_options",
		callback: (r) => {
			const options = (r.message || []).map((row) => row.value || row.code || row).join("\n");
			fields.business_domain.df.options = options;
			fields.business_domain.refresh();
		},
	});

	function values() {
		const out = {};
		Object.keys(fields).forEach((key) => (out[key] = fields[key].get_value()));
		return out;
	}

	function validate_required(data) {
		for (const key of ["company", "business_domain", "accounting_regime", "vat_method"]) {
			if (!data[key]) {
				frappe.msgprint(__("Please complete all required fields."));
				return false;
			}
		}
		return true;
	}

	page.add_button(__("Preview"), () => {
		const data = values();
		if (!validate_required(data)) return;
		frappe.call({
			method: "erpnext_vietnam.setup.setup_wizard.preview_localization_profile",
			args: { args: data },
			callback: (r) => {
				const result = r.message || {};
				const warnings = (result.warnings || []).map((x) => `<li>${frappe.utils.escape_html(x)}</li>`).join("");
				const changes = (result.changes || []).map((x) => `<li>${frappe.utils.escape_html(x)}</li>`).join("");
				frappe.msgprint({
					title: __("Setup Preview"),
					indicator: warnings ? "orange" : "blue",
					message: `<p><b>${__("Snapshot hash")}:</b> ${frappe.utils.escape_html(result.snapshot_hash || "")}</p><p><b>${__("Planned changes")}:</b></p><ul>${changes}</ul>${warnings ? `<p><b>${__("Warnings")}:</b></p><ul>${warnings}</ul>` : ""}`,
				});
			},
		});
	});

	page.set_primary_action(__("Apply Setup"), () => {
		const data = values();
		if (!validate_required(data)) return;
		frappe.confirm(
			__("Apply this Vietnam localization profile? This does not enable external government submissions."),
			() => frappe.call({
				method: "erpnext_vietnam.setup.setup_wizard.apply_localization_profile",
				args: { args: data },
				freeze: true,
				freeze_message: __("Applying Vietnam localization setup..."),
				callback: (r) => frappe.msgprint(__("Vietnam localization setup applied. Compliance Gateway remains disabled.")),
			})
		);
	});
};
