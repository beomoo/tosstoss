"""Explicit frozen relational inventory; migrations are not runtime dependencies."""

from dataclasses import dataclass
from typing import Any

from . import canonical as c

PENDING_FIELDS = """counter_capability_registration_id contract_version
reviewer_credential_operation_id operation_content_hash operation_type reviewer_principal_id
reviewer_role principal_content_hash os_owner_sid_hash expected_credential_state_hash
registration_challenge_id registration_challenge_purpose registration_challenge_binding_hash
prerequisite_authentication_event_id prerequisite_authentication_content_hash
prerequisite_authentication_result webauthn_credential_id credential_id_fingerprint
cose_public_key_canonical public_key_fingerprint public_key_algorithm authenticator_aaguid
authenticator_attachment authenticator_transports_json rp_id exact_origin resident_key_required
require_resident_key user_verification_required attestation_conveyance cred_props_requested
cred_props_rk registration_policy_version observed_registration_sign_count client_data_type_verified
challenge_verified origin_verified cross_origin_false_verified rp_id_hash_verified
user_presence_verified user_verification_verified platform_authenticator_verified
resident_key_verified
public_key_material_verified safe_result_code continuation_challenge_id""".split()
CHILD_FIELDS = """counter_capability_challenge_id contract_version challenge_digest
challenge_nonce_length challenge_purpose counter_capability_registration_id
counter_capability_registration_content_hash reviewer_credential_operation_id operation_content_hash
operation_type reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash
expected_credential_state_hash parent_registration_challenge_id
parent_registration_challenge_binding_hash
webauthn_credential_id credential_id_fingerprint public_key_fingerprint rp_id allowed_origin
client_data_type user_verification_required allow_credentials_count allowed_webauthn_credential_id
user_handle_contract_version authentication_policy_version issued_at expires_at""".split()
BOOTSTRAP_FIELDS = """counter_capability_assertion_id contract_version
counter_capability_challenge_id
challenge_binding_hash counter_capability_registration_id
counter_capability_registration_content_hash
reviewer_credential_operation_id operation_content_hash operation_type reviewer_principal_id
reviewer_role principal_content_hash os_owner_sid_hash expected_credential_state_hash
webauthn_credential_id credential_id_fingerprint public_key_fingerprint challenge_terminal_result
safe_result_code client_data_type_verified challenge_verified origin_verified
cross_origin_false_verified
rp_id_hash_verified user_presence_verified user_verification_verified credential_id_verified
signature_verified replay_rejected user_handle_status observed_registration_sign_count
previous_sign_count asserted_sign_count selected_counter_capability selected_registration_sign_count
classification_verified projected_registration_consumption_id
projected_registration_consumption_content_hash
projected_registration_challenge_purpose projected_registration_terminal_result
projected_registration_safe_result_code projected_operation_outcome_id
projected_operation_outcome_content_hash
projected_operation_terminal_result projected_resulting_credential_state_hash
projected_credential_content_hash
projected_registered_event_id projected_registered_event_content_hash
projected_registered_authorization_content_hash projected_superseded_event_id
projected_superseded_event_content_hash projected_superseded_authorization_content_hash""".split()


@dataclass(frozen=True)
class Table:
    name: str
    key: str
    hash_column: str
    version: str
    fields: list[str]
    time_column: str | None

    def hash(self, row: dict[str, Any]) -> str:
        values = dict(row)
        if self is CREDENTIAL:
            values["authenticator_transports"] = c.strict_json(row["authenticator_transports_json"])
        return c.row_hash(values, self.fields)


PRINCIPAL = Table(
    "reviewer_principals",
    "reviewer_principal_id",
    "principal_content_hash",
    c.POLICY,
    c.PRINCIPAL_FIELDS,
    "registered_at",
)
CREDENTIAL = Table(
    "reviewer_webauthn_credentials",
    "webauthn_credential_id",
    "credential_content_hash",
    c.POLICY,
    c.CREDENTIAL_FIELDS,
    "registered_at",
)
EVENT = Table(
    "reviewer_webauthn_credential_events",
    "credential_event_id",
    "credential_event_content_hash",
    c.POLICY,
    c.EVENT_FIELDS,
    "occurred_at",
)
OPERATION = Table(
    "reviewer_credential_operations",
    "reviewer_credential_operation_id",
    "operation_content_hash",
    "reviewer-credential-operation/0.1.0",
    c.OPERATION_FIELDS,
    "created_at",
)
CHALLENGE = Table(
    "reviewer_credential_operation_challenges",
    "reviewer_credential_operation_challenge_id",
    "challenge_binding_hash",
    "reviewer-credential-operation-challenge/0.1.0",
    c.CHALLENGE_FIELDS,
    None,
)
CONSUMPTION = Table(
    "reviewer_credential_operation_challenge_consumptions",
    "challenge_consumption_id",
    "consumption_content_hash",
    "reviewer-credential-operation-consumption/0.1.0",
    c.CONSUMPTION_FIELDS,
    "consumed_at",
)
AUTHENTICATION = Table(
    "reviewer_credential_operation_authentication_events",
    "credential_operation_authentication_event_id",
    "authentication_content_hash",
    "reviewer-credential-operation-authentication/0.1.0",
    c.AUTHENTICATION_FIELDS,
    "authenticated_at",
)
AUTHORIZATION = Table(
    "reviewer_webauthn_credential_event_authorizations",
    "credential_event_id",
    "authorization_content_hash",
    "reviewer-credential-event-authorization/0.1.0",
    c.AUTHORIZATION_FIELDS,
    "recorded_at",
)
OUTCOME = Table(
    "reviewer_credential_operation_outcomes",
    "credential_operation_outcome_id",
    "outcome_content_hash",
    "reviewer-credential-operation-outcome/0.1.0",
    c.OUTCOME_FIELDS,
    "completed_at",
)
PENDING = Table(
    "reviewer_webauthn_counter_capability_registrations",
    "counter_capability_registration_id",
    "counter_capability_registration_content_hash",
    "reviewer-counter-capability-registration/0.1.0",
    PENDING_FIELDS,
    "verified_at",
)
CHILD = Table(
    "reviewer_webauthn_counter_capability_challenges",
    "counter_capability_challenge_id",
    "challenge_binding_hash",
    "reviewer-counter-capability-challenge/0.1.0",
    CHILD_FIELDS,
    None,
)
BOOTSTRAP = Table(
    "reviewer_webauthn_counter_capability_assertions",
    "counter_capability_assertion_id",
    "assertion_content_hash",
    "reviewer-counter-capability-assertion/0.1.0",
    BOOTSTRAP_FIELDS,
    "consumed_at",
)
ISSUER_AUTHENTICATION = Table(
    "reviewer_authentication_events",
    "authentication_event_id",
    "authentication_content_hash",
    c.POLICY,
    c.ISSUER_AUTHENTICATION_FIELDS,
    "authenticated_at",
)
WRITE_TABLES = (
    PRINCIPAL,
    CREDENTIAL,
    EVENT,
    OPERATION,
    CHALLENGE,
    CONSUMPTION,
    AUTHENTICATION,
    AUTHORIZATION,
    OUTCOME,
    PENDING,
    CHILD,
    BOOTSTRAP,
)
READ_TABLES = (*WRITE_TABLES, ISSUER_AUTHENTICATION)


def sealed(table: Table, row: dict[str, Any]) -> dict[str, Any]:
    result = {**row, "contract_version": table.version, "payload_json": "{}"}
    result[table.hash_column] = table.hash(result)
    return result
