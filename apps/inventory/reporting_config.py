from decimal import Decimal


# These are reporting defaults, not official national stock policies.
# They will become configurable organization/facility settings later.

DEFAULT_LOW_COVERAGE_MONTHS = Decimal("1.0")
DEFAULT_CRITICAL_COVERAGE_MONTHS = Decimal("0.5")
DEFAULT_HIGH_COVERAGE_MONTHS = Decimal("6.0")

DEFAULT_NEAR_EXPIRY_DAYS = 90

DEFAULT_AMC_MONTHS = 3

MAX_REPORTING_AMC_MONTHS = 24