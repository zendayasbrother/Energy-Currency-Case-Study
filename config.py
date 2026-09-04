
SERIES_MAPPING = {
    'A-FP.CPI.TOTL.ZG': 'inflation',
    'ENDE_XDC_USD_RATE': 'exchange_rate',
    'NE.CON.PRVT.CD': 'hfce'
}

COUNTRY_ISO_MAP = {
    288: "GHA",
    566: "NGA",
    156: "CHN"
}

API_CONFIG = {
    "comtrade_periods": "2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024",
    "cmd_codes": "854143,271600",
}

DB_CONFIG = {
    "schema": "Trade Intelligence",
    "bilateral_table": "bilateral_trade",
    "stability_table": "currency_stability"
}