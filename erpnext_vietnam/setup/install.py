from __future__ import annotations


def after_install():
    # Safe seed only: domain profiles are reference data and do not enable compliance.
    from erpnext_vietnam.setup.setup_wizard import sync_business_profiles

    sync_business_profiles()
