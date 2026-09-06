from __future__ import annotations


def _sync_reference_data():
    from erpnext_vietnam.setup.setup_wizard import sync_business_profiles
    from erpnext_vietnam.setup.custom_fields import sync_custom_fields
    from erpnext_vietnam.setup.p1_seed import seed_p1_reference_data

    sync_business_profiles()
    sync_custom_fields()
    seed_p1_reference_data()


def after_install():
    # Safe reference/config seed only. No Company is configured and no external integration is enabled.
    _sync_reference_data()


def after_migrate():
    # Idempotently keep app-owned Custom Fields and released reference datasets present.
    _sync_reference_data()
