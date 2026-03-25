import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import httpx
from pywizlight import wizlight
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from db import get_total_energy_and_cost, init_db, save_consumption, save_price

# load configuration to make it simpler hardcoded values
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
with open(CONFIG_PATH) as f:
    config = json.load(f)

bulb_ip = config["bulb_ip"]
MAX_WATTAGE = config["max_wattage"]
PRICE_HIGH = config["price_thresholds"]["high"]
PRICE_LOW = config["price_thresholds"]["low"]
API_FETCH_INTERVAL = config["api_refresh_interval"]
API_CURRENT_PRICE = config["api_endpoints"]["current_price"]
API_PRICE_LEVEL = config["api_endpoints"]["price_level"]

console = Console()

# cache API
cached_price = 0.0
cached_level = "unknown"
last_api_fetch = 0

# history consumption to calculate average price
consumption_history = []

# function to get spot price and recommendation from spotovaelektrina.cz
async def get_spot_price():
    global cached_price, cached_level, last_api_fetch

    # if the last API fetch was less than API_FETCH_INTERVAL ago, don't use API
    now = time.time()
    if (now - last_api_fetch) < API_FETCH_INTERVAL and last_api_fetch != 0:
        return cached_price, cached_level

    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # get actual price in CZK/MWh
        try:
            price = await client.get(API_CURRENT_PRICE)
            cached_price = price.json().get("priceCZK", 0.0)

        except Exception:
            pass

        # check level (NÍZKÉ, STŘEDNÍ, VYSOKÉ)
        try:
            level = await client.get(API_PRICE_LEVEL)
            level_data = level.text.lower()
            if "low" in level_data:
                cached_level = "low"
            elif "high" in level_data:
                cached_level = "high"
            else:
                cached_level = "medium"

        except Exception:
            cached_level = "error"

        # fallback level based on my own logic (when api doesnt want to listen)
        numeric_level = "medium"
        if cached_price >= PRICE_HIGH:
            numeric_level = "high"
        elif cached_price <= PRICE_LOW:
            numeric_level = "low"

        if cached_level not in {"low", "medium", "high"} or cached_level == "error":
            cached_level = numeric_level
        else:
            # always bump to high/low to prevent being stuck in medium
            if numeric_level == "high":
                cached_level = "high"
            elif numeric_level == "low":
                cached_level = "low"

        # save price to database
        if cached_price > 0:
            save_price(cached_price, cached_level)

    last_api_fetch = now
    return cached_price, cached_level

async def get_bulb_data(light):
    global consumption_history
    try:
        state = await light.updateState()
        is_on = state.get_state()

        consumption = 0.0

        if is_on:
            raw_state = light.state.pilotResult
            c_raw = raw_state.get("consumptionRateInHour", raw_state.get("pc"))

            if c_raw is not None and float(c_raw) > 0:
                consumption = float(c_raw)

            else:
                brightness = state.get_brightness()
                if brightness is None:
                    brightness = 255

                consumption = (brightness / 255.0) * MAX_WATTAGE

        if is_on and consumption > 0:
            consumption_history.append(consumption)
            if len(consumption_history) > 100:
                consumption_history.pop(0)

        avg_cons = (
            sum(consumption_history) / len(consumption_history)
            if consumption_history
            else 0.0
        )

        state_str = (
            "[bold green]ZAPNUTO[/bold green]"
            if is_on
            else "[bold red]VYPNUTO[/bold red]"
        )
        power_str = f"{consumption:.1f} W (Ø od startu: {avg_cons:.1f} W)"

        return state_str, power_str, is_on, consumption

    except Exception as e:
        return f"[bold red]CHYBA:[/bold red] {type(e).__name__}", "N/A", False, 0.0


def dashboard(bulb_state, bulb_power, current_price, price_status, energy_wh_total=0.0, cost_czk_total=0.0):

    # home devices table
    device_table = Table(box=box.ROUNDED, expand=True)
    device_table.add_column("Zařízení", justify="center")
    device_table.add_column("Stav", justify="center")
    device_table.add_column("Spotřeba (Aktuální | Průměrná)", justify="right", style="magenta")
    device_table.add_row("Chytrá žárovka", bulb_state, bulb_power)

    # market api table
    market_table = Table(box=box.ROUNDED, expand=True)
    market_table.add_column("Sledovaný ukazatel", justify="center", style="white")
    market_table.add_column("Aktuální cena", justify="center")
    market_table.add_column("Status sítě", justify="center")

    # colored price based on price level api returns
    if price_status == "low":
        price_str = f"[bold green]{current_price} Kč/MWh[/bold green]"
        action_str = "[bold green]NÍZKÝ TARIF, VHODNÉ ZAPNOUT SPOTŘEBIČE[/bold green]"
    elif price_status == "high":
        price_str = f"[bold red]{current_price} Kč/MWh[/bold red]"
        action_str = "[bold red]VYSOKÝ TARIF, ŠETŘETE[/bold red]"
    elif price_status == "error":
        price_str = f"[bold red]{current_price} Kč/MWh[/bold red]"
        action_str = "[bold red]ERROR[/bold red]"
    else:
        price_str = f"[yellow]{current_price} Kč/MWh[/yellow]"
        action_str = "[yellow]BĚŽNÝ PROVOZ[/yellow]"

    # last api fetch time
    api_time = (
        datetime.fromtimestamp(last_api_fetch).strftime("%H:%M:%S")
        if last_api_fetch
        else "..."
    )

    market_table.add_row(f"Aktuální cena (Aktualizováno {api_time})", price_str, action_str)
    market_table.add_row("Spotřeba (celkem)", f"[dim]{energy_wh_total:.1f} Wh[/dim]", "")
    market_table.add_row("Odhadovaný náklad", f"[bold yellow]{cost_czk_total:.2f} Kč[/bold yellow]", "")

    # dashboard layout
    layout = Layout()
    layout.split_column(
        Layout(
            Panel(
                market_table,
                title="[bold] Energetický trh v ČR[/bold]",
                border_style = "green",
            )
        ),
        Layout(
            Panel(
                device_table,
                title="[bold] Domácí zařízení[/bold]",
                border_style = "green",
            )
        ),
    )

    now = datetime.now().strftime("[bold white]%Y-%m-%d %H:%M:%S[/bold white]")
    return Panel(
        layout,
        title=f"[bold white]Terminál energetického systému[/bold white] | {now}",
        border_style="white",
        padding=(1, 1),
    )


async def main():
    init_db()  # initialize database on startup
    
    light = wizlight(bulb_ip)
    console.clear()

    try:
        # load all energy and cost from database
        historical_energy, historical_cost = get_total_energy_and_cost()
        
        # display totals (historical + current session)
        energy_wh_total = historical_energy
        cost_czk_total = historical_cost
        last_cost_ts = time.time()

        with Live(
            dashboard("Načítam...", "Načítam...", 0, "unknown", energy_wh_total, cost_czk_total),
            refresh_per_second=2,
            screen=True,
        ) as live:
            while True:
                state, power, is_on, consumption = await get_bulb_data(light)
                price, level = await get_spot_price()

                now = time.time()
                dt = now - last_cost_ts
                last_cost_ts = now

                if is_on and consumption > 0 and price > 0 and dt > 0:
                    # calculate energy and cost for this interval
                    energy_wh = consumption * dt / 3600.0
                    cost_czk = energy_wh * (price / 1_000_000.0)
                    
                    energy_wh_total += energy_wh
                    cost_czk_total += cost_czk
                    
                    # save
                    save_consumption(consumption, energy_wh, cost_czk)

                live.update(
                    dashboard(
                        state,
                        power,
                        price,
                        level,
                        energy_wh_total,
                        cost_czk_total,
                    )
                )
                await asyncio.sleep(2)

    except KeyboardInterrupt:
        pass
    finally:
        await light.async_close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if str(e) != "Event loop is closed":
            raise
