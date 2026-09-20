# Harvested by harvest_parts.py
# capability : CAP-0013 (calculate tax)
# from       : payroll-tax-calculator @ af699c7d3a12f66b9ff9a88a97f193743f58c04e
# source     : salary_engine.py:3-105
# licence    : Apache-2.0 (LICENSE)
# NOTE: this file is evidence, not a standalone module -- it depends on names from the source application's own modules (see PROVENANCE.json 'dependencies'). It is not imported directly; build.py binds it into a verified, running instance of the source application.

def calculate_payroll_details(basic_salary, bonus=0.0, working_days=26, unpaid_leaves=0, tax_slabs=[]):
    """
    Calculates gross salary, deductions (PF, PT, Insurance, Tax), and net salary.
    Pro-rates basic salary and allowances based on unpaid leaves.
    Projects annual taxable income and calculates progressive tax.
    
    Parameters:
      basic_salary (float): Base monthly salary
      bonus (float): One-time monthly bonus
      working_days (int): Total working days in the month (default 26)
      unpaid_leaves (int): Count of unpaid leaves taken (default 0)
      tax_slabs (list): List of dicts representing tax slabs:
                        [{'min_income': 0, 'max_income': 300000, 'tax_rate': 0.0}, ...]
    """
    # 1. Pro-rating factor
    if working_days <= 0:
        working_days = 26
    
    unpaid_leaves = max(0, min(working_days, unpaid_leaves))
    payable_days = working_days - unpaid_leaves
    prorate_factor = payable_days / working_days

    # 2. Earnings (allowances)
    prorated_basic = basic_salary * prorate_factor
    hra = prorated_basic * 0.40 # 40% HRA
    da = prorated_basic * 0.10  # 10% DA
    medical_allowance = 1250.0 * prorate_factor
    travel_allowance = 1600.0 * prorate_factor
    
    gross_salary = prorated_basic + hra + da + medical_allowance + travel_allowance + bonus

    # 3. Deductions (fixed & percentage-based)
    pf = prorated_basic * 0.12 # 12% PF on basic
    professional_tax = 200.0 if prorated_basic > 15000.0 else 0.0 # PT standard
    insurance = 1000.0 if basic_salary > 25000.0 else 500.0 # Insurance standard

    # 4. Income Tax Calculation
    # Project annual gross income: pro-rated monthly regular gross * 12 + this month's bonus
    regular_monthly_gross = (basic_salary + (basic_salary * 0.40) + (basic_salary * 0.10) + 1250.0 + 1600.0) * prorate_factor
    projected_annual_gross = (regular_monthly_gross * 12.0) + bonus
    
    # Apply Standard Deduction
    standard_deduction = 75000.0
    taxable_income = max(0.0, projected_annual_gross - standard_deduction)

    # Progressive tax calculation
    annual_tax = 0.0
    
    # Default slabs if none provided (Indian New Tax Regime FY 2025-26)
    active_slabs = tax_slabs if tax_slabs else [
        {'min_income': 0.0, 'max_income': 300000.0, 'tax_rate': 0.00},
        {'min_income': 300000.0, 'max_income': 700000.0, 'tax_rate': 0.05},
        {'min_income': 700000.0, 'max_income': 1000000.0, 'tax_rate': 0.10},
        {'min_income': 1000000.0, 'max_income': 1500000.0, 'tax_rate': 0.15},
        {'min_income': 1500000.0, 'max_income': None, 'tax_rate': 0.20}
    ]

    # Calculate progressive tax
    for slab in sorted(active_slabs, key=lambda x: x['min_income']):
        min_i = slab['min_income']
        max_i = slab['max_income']
        rate = slab['tax_rate']
        
        if taxable_income > min_i:
            if max_i is None or taxable_income <= max_i:
                annual_tax += (taxable_income - min_i) * rate
                break
            else:
                annual_tax += (max_i - min_i) * rate

    # Tax rebate under Section 87A (New Tax Regime):
    # If projected annual taxable income (before rebate, but after standard deduction)
    # does not exceed ₹7,00,000, the tax rebate is 100% (tax becomes 0).
    # We apply this specifically for the default or standard regime.
    # We can tie it to whether the taxable income is <= 7 Lakhs.
    if projected_annual_gross - standard_deduction <= 700000.0:
        annual_tax = 0.0

    monthly_tax = annual_tax / 12.0
    
    # 5. Net Salary
    net_salary = gross_salary - pf - professional_tax - monthly_tax - insurance

    return {
        'basic_salary': round(prorated_basic, 2),
        'hra': round(hra, 2),
        'da': round(da, 2),
        'bonus': round(bonus, 2),
        'medical_allowance': round(medical_allowance, 2),
        'travel_allowance': round(travel_allowance, 2),
        'gross_salary': round(gross_salary, 2),
        'pf': round(pf, 2),
        'professional_tax': round(professional_tax, 2),
        'income_tax': round(monthly_tax, 2),
        'insurance': round(insurance, 2),
        'net_salary': round(net_salary, 2),
        'working_days': working_days,
        'unpaid_leaves': unpaid_leaves,
        'payable_days': payable_days,
        'projected_annual_gross': round(projected_annual_gross, 2),
        'taxable_income': round(taxable_income, 2),
        'annual_tax': round(annual_tax, 2)
    }
