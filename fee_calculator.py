"""
RentTrust UZ — Pure Fee Calculator Module
Pure function to calculate rental fees, deposits, platform split commission and payouts.
"""

def calculate_fees(monthly_rent: float | int, deposit: float | int = 0) -> dict:
    """
    Pure function to calculate platform commission and totals.
    Rules:
    - Commission is 2% of monthly rent from tenant and 2% from landlord, charged at funding.
    - Deposit has 0% commission.
    Example:
    - Rent: 3,000,000 UZS, Deposit: 0 UZS
      -> Tenant fee (2%): 60,000 UZS
      -> Landlord fee (2%): 60,000 UZS
      -> Total platform fee: 120,000 UZS
      -> Tenant pays: 3,060,000 UZS (+ deposit)
      -> Landlord receives: 2,940,000 UZS
      -> Platform keeps: 120,000 UZS
    """
    monthly_rent = float(monthly_rent)
    deposit = float(deposit)

    if monthly_rent < 0:
        raise ValueError("Monthly rent cannot be negative")
    if deposit < 0:
        raise ValueError("Deposit cannot be negative")

    tenant_fee = round(monthly_rent * 0.02)
    landlord_fee = round(monthly_rent * 0.02)
    platform_fee = tenant_fee + landlord_fee

    tenant_total = round(monthly_rent + tenant_fee + deposit)
    landlord_receives = round(monthly_rent - landlord_fee)

    # Hold amount: 10% of monthly rent (part of the first payment, not separate fee)
    hold_amount = max(300000, round(monthly_rent * 0.10))
    remainder = max(0, round((monthly_rent + deposit) - hold_amount))

    return {
        "monthly_rent": monthly_rent,
        "deposit": deposit,
        "tenant_fee": tenant_fee,
        "landlord_fee": landlord_fee,
        "platform_fee": platform_fee,
        "tenant_total": tenant_total,
        "landlord_receives": landlord_receives,
        "hold_amount": hold_amount,
        "remainder": remainder
    }
