import json
import urllib.request
import urllib.parse
from typing import Dict, Any

# Common currency symbol mapping for clear display
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "ZAR": "R",
    "JPY": "¥",
    "CAD": "CA$",
    "AUD": "A$",
    "CNY": "¥",
    "INR": "₹",
    "BRL": "R$",
    "BTC": "₿"
}

def convert_currency(amount: float = 1.0, from_currency: str = "USD", to_currency: str = "ZAR") -> str:
    """
    Convert an amount from one currency to another using keyless real-time exchange rate endpoints.
    
    Args:
        amount: The numerical monetary value to convert (defaults to 1.0).
        from_currency: 3-letter source currency code (e.g. 'USD', 'EUR', 'GBP', 'ZAR', 'BTC').
        to_currency: 3-letter target currency code (e.g. 'ZAR', 'USD', 'EUR', 'GBP').
    """
    base = from_currency.strip().upper()
    target = to_currency.strip().upper()
    
    if base == target:
        return f"🔀 **Currency Exchange:** {amount:.2f} {base} is equal to **{amount:.2f} {target}** (1:1)."

    try:
        # 1. Primary Endpoint: Open Exchange Rates API (Keyless)
        primary_url = f"https://open.er-api.com/v6/latest/{base}"
        req = urllib.request.Request(primary_url, headers={"User-Agent": "FRIDAY-Assistant/1.0"})
        
        rates = {}
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            if data.get("result") == "success":
                rates = data.get("rates", {})
        
        # 2. Fallback Endpoint if primary fails or target missing: Frankfurter API
        if not rates or target not in rates:
            fallback_url = f"https://api.frankfurter.app/latest?from={base}&to={target}"
            f_req = urllib.request.Request(fallback_url, headers={"User-Agent": "FRIDAY-Assistant/1.0"})
            with urllib.request.urlopen(f_req, timeout=8) as f_resp:
                f_data = json.loads(f_resp.read().decode())
                rates = f_data.get("rates", {})
        
        if target not in rates:
            return f"Error: Could not retrieve real-time conversion rate from '{base}' to '{target}'."
        
        rate = float(rates[target])
        converted = amount * rate
        
        src_symbol = CURRENCY_SYMBOLS.get(base, "")
        tgt_symbol = CURRENCY_SYMBOLS.get(target, "")
        
        src_formatted = f"{src_symbol}{amount:,.2f}" if src_symbol else f"{amount:,.2f} {base}"
        tgt_formatted = f"{tgt_symbol}{converted:,.2f}" if tgt_symbol else f"{converted:,.2f} {target}"
        
        report = (
            f"🔀 **Currency Exchange Update:**\n"
            f"- **Conversion:** {src_formatted} ➔ **{tgt_formatted}**\n"
            f"- **Exchange Rate:** 1 {base} = {rate:,.4f} {target}\n"
            f"- **Inverse Rate:** 1 {target} = {(1/rate):,.4f} {base}"
        )
        return report
        
    except Exception as e:
        return f"Error converting {amount} {base} to {target}: {str(e)}"

def register(mcp):
    """Register currency tools on the FastMCP server."""
    mcp.tool()(convert_currency)
