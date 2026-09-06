frappe.provide("erpnext_vietnam.setup");

frappe.setup.on("before_load", function () {
	frappe.setup.add_slide({
		name: "erpnext-vietnam-profile",
		title: __("Vietnam localization"),
		icon: "fa fa-flag",
		fields: [
			{ fieldname: "vn_business_profile", label: __("Business Domain"), fieldtype: "Select", reqd: 1, options: ["GENERAL_SERVICES", "SOFTWARE_SAAS", "RETAIL", "WHOLESALE_DISTRIBUTION", "MANUFACTURING", "REAL_ESTATE", "HOSPITALITY", "HEALTHCARE", "EDUCATION", "AGRICULTURE", "LOGISTICS", "CONSTRUCTION", "PROFESSIONAL_SERVICES", "NONPROFIT", "OTHER"].join("\n"), default: "GENERAL_SERVICES", description: __("A preset only. Legal rules remain effective-dated and independently governed.") },
			{ fieldname: "vn_accounting_regime", label: __("Vietnam Accounting Regime"), fieldtype: "Select", reqd: 1, options: "TT99_2025\nTT133_2016\nCUSTOM_REVIEW_REQUIRED", default: "TT99_2025" },
			{ fieldname: "vn_vat_method", label: __("VAT Method"), fieldtype: "Select", reqd: 1, options: "DEDUCTION\nDIRECT\nNOT_CONFIGURED", default: "DEDUCTION" },
			{ fieldtype: "Section Break", label: __("Compliance Features") },
			{ fieldname: "vn_enable_payroll_compliance", label: __("Enable PIT payroll compliance"), fieldtype: "Check", default: 1 },
			{ fieldname: "vn_enable_social_insurance", label: __("Enable BHXH / BHYT / BHTN"), fieldtype: "Check", default: 1 },
			{ fieldname: "vn_enable_einvoice", label: __("Prepare e-invoice integration"), fieldtype: "Check", default: 0 },
			{ fieldtype: "HTML", options: __("External tax/BHXH submission is never enabled automatically. The Compliance Gateway remains disabled until an administrator configures and validates an adapter.") },
		],
	});
});
