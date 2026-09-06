import hashlib
import unittest

from erpnext_vietnam.integration.certification import (
    AdapterCertification, CertificationArtifact, CertificationValidationError, certification_hash,
)
from erpnext_vietnam.integration.registry import register, require_production_certification


class FakeAdapter:
    channel = "E_INVOICE"
    capabilities = frozenset({"VALIDATE"})
    def __init__(self, adapter_id): self.adapter_id = adapter_id


def sha(text): return hashlib.sha256(text.encode()).hexdigest()


def cert(adapter_id):
    return AdapterCertification(
        adapter_id=adapter_id, channel="E_INVOICE", certification_version="v1", provider_name="Provider",
        reviewed_on="2026-09-06", artifacts=(
            CertificationArtifact("API_SPEC", "official://api", "v1", sha("api")),
            CertificationArtifact("PAYLOAD_SCHEMA", "official://schema", "v1", sha("schema")),
        ),
    )


class TestP4ECertification(unittest.TestCase):
    def test_hash_is_stable_and_requires_contract_plus_schema(self):
        c = cert("test.certified.one")
        self.assertEqual(certification_hash(c), certification_hash(c))
        bad = AdapterCertification(
            adapter_id="test.bad", channel="E_INVOICE", certification_version="v1", provider_name="Provider",
            reviewed_on="2026-09-06", artifacts=(CertificationArtifact("API_SPEC", "official://api", "v1", sha("api")),),
        )
        with self.assertRaises(CertificationValidationError):
            certification_hash(bad)

    def test_registry_rejects_certification_identity_mismatch(self):
        adapter = FakeAdapter("test.certified.two")
        with self.assertRaisesRegex(ValueError, "adapter_id does not match"):
            register(adapter, cert("another.adapter"))

    def test_production_certification_is_explicit(self):
        uncertified = FakeAdapter("test.uncertified.three")
        register(uncertified)
        with self.assertRaisesRegex(ValueError, "not production-certified"):
            require_production_certification(uncertified.adapter_id, uncertified.channel)
        certified = FakeAdapter("test.certified.four")
        c = cert(certified.adapter_id)
        register(certified, c)
        self.assertEqual(require_production_certification(certified.adapter_id, certified.channel), c)


if __name__ == "__main__": unittest.main()
