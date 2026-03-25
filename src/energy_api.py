from datetime import datetime

import requests


def get_spot_tarrifs_data():
    """Stáhne aktuální data o spotových tarifech pro ČR z API Energy-Charts."""

    url = "https://api.energy-charts.info/price?price_step=1h&location=cz"

    try:
        response = requests.get(url)
        response.raise_for_status()  # checking, if the request was succesful
        data = response.json()

        # unix timestamp
        timestamps = data["unix_seconds"]
        prices = data["price"]  # in EUR/MWh

        now_timestamps = datetime.now().timestamp()

        # find index of the current hour
        current_index = 0
        for i, ts in enumerate(timestamps):
            if ts <= now_timestamps < (ts + 3600):
                current_index = i
                break

        current_price = prices[current_index]
        avg_price = sum(prices) / len(prices)

        print(f"Aktuální spotová cena: {current_price:.2f} EUR/MWh")
        print(f"Dnešní průměrná cena: {avg_price:.2f} EUR/MWh")

        # decides to tell if the average price is higher or lower by 10%
        if current_price < (avg_price * 0.9):
            return "LEVNÉ", current_price
        elif current_price > (avg_price * 1.1):
            return "DRAHÉ", current_price
        else:
            return "NORMÁLNÍ", current_price

    except Exception as e:
        print(f"Chyba při stažení dat o spotových tarifech: {e}")
        return "NEZNÁMÉ", 0
