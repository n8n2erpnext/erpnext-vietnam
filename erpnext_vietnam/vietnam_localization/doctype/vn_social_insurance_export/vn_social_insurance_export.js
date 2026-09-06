function download_review(frm, method, format) {
    const params = new URLSearchParams({ name: frm.doc.name, export_format: format });
    window.open(`/api/method/${method}?${params.toString()}`, "_blank", "noopener");
}

frappe.ui.form.on("VN Social Insurance Export", {
    refresh(frm) {
        if (frm.is_new() || frm.doc.status === "Voided" || frm.doc.adapter_status !== "Ready") {
            return;
        }
        frm.add_custom_button(__("Review XLSX"), () => {
            download_review(frm, "erpnext_vietnam.declarations.service.download_social_insurance_export_review", "xlsx");
        }, __("Export"));
        frm.add_custom_button(__("Review XML"), () => {
            download_review(frm, "erpnext_vietnam.declarations.service.download_social_insurance_export_review", "xml");
        }, __("Export"));
    },
});
