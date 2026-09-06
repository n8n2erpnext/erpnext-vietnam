from erpnext_vietnam.integration.adapters.sandbox import sandbox_einvoice_adapter
from erpnext_vietnam.integration.registry import register


def register_builtin_adapters() -> None:
    register(sandbox_einvoice_adapter)
