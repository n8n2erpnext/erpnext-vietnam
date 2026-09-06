frappe.ui.form.on("Global Defaults", {
	refresh(frm) {
		frm.fields_dict.vn_open_localization_setup?.$input?.off("click.vn").on("click.vn", () => {
			frappe.set_route("vn-setup-wizard");
		});
		frm.fields_dict.vn_open_localization_health?.$input?.off("click.vn").on("click.vn", () => {
			frappe.set_route("vn-localization-health");
		});

		const host = frm.fields_dict.vn_localization_status_html?.$wrapper;
		if (!host) return;
		const company = frm.doc.default_company;
		if (!company) {
			host.html(`<div class="text-muted">${__("Choose a Default Company to view Vietnam Localization status.")}</div>`);
			return;
		}

		host.html(`<div class="text-muted">${__("Loading Vietnam Localization status...")}</div>`);
		frappe.call({
			method: "erpnext_vietnam.diagnostics.health.get_health",
			args: { company },
			callback: (r) => {
				const h = r.message || {};
				const setup = h.setup || {};
				const gateway = setup.enable_compliance_gateway ? __("Enabled") : __("Disabled");
				const warningCount = (h.warnings || []).length;
				const status = frappe.utils.escape_html(h.overall_status || __("Not configured"));
				const profile = frappe.utils.escape_html(setup.business_profile || "—");
				const regime = frappe.utils.escape_html(setup.accounting_regime || "—");
				const vat = frappe.utils.escape_html(setup.vat_method || "—");
				host.html(
					`<div class="small">` +
					`<b>${__("Status")}:</b> ${status} &nbsp; · &nbsp; ` +
					`<b>${__("Profile")}:</b> ${profile} &nbsp; · &nbsp; ` +
					`<b>${__("Accounting")}:</b> ${regime} &nbsp; · &nbsp; ` +
					`<b>${__("VAT")}:</b> ${vat}<br>` +
					`<b>${__("Compliance Gateway")}:</b> ${gateway}` +
					(warningCount ? ` &nbsp; · &nbsp; <b>${__("Warnings")}:</b> ${warningCount}` : "") +
					`</div>`
				);
			},
		});
	},
});
