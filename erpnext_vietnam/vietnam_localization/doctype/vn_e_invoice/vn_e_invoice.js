function vn_einvoice_action(frm, method) {
    frappe.call({
        method,
        args: { name: frm.doc.name },
        freeze: true,
        callback: () => frm.reload_doc(),
    });
}

frappe.ui.form.on("VN E-Invoice", {
    refresh(frm) {
        if (frm.is_new()) return;
        if (frm.doc.status === "PREPARED") {
            frm.add_custom_button(__("Queue for Submission"), () =>
                vn_einvoice_action(frm, "erpnext_vietnam.einvoice.gateway.queue"), __("Compliance"));
        } else if (frm.doc.status === "QUEUED") {
            frm.add_custom_button(__("Submit"), () =>
                vn_einvoice_action(frm, "erpnext_vietnam.einvoice.gateway.submit"), __("Compliance"));
        } else if (["UNKNOWN", "SUBMITTING"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Reconcile"), () =>
                vn_einvoice_action(frm, "erpnext_vietnam.einvoice.gateway.reconcile"), __("Compliance"));
        }
    },
});
