# dynamic spot tariffs with my smart bulb monitoring

app that tracks electricity prices and bulb costs in real time. fetches prices from spotovaelektrina.cz, checks if the bulb is on, and stores all the data so you can see how much money you're wasting.

## what it does

the app runs in a terminal and shows you the current electricity price. it checks your smart bulb every 2 seconds to see if its on. when the bulb uses power, it calculates the cost based on the current price and stores it. all data is saved in a database so if you restart the app, you dont lose the total cost.

## setup

you need:
- python 3.14 or later
- smart bulb on your network (WIZ type, default IP 192.168.0.46)
- internet to reach the energy API

install:
```bash
python -m venv .venv
source .venv/Scripts/activate  # on Windows use: .venv\Scripts\activate
pip install httpx pywizlight rich
```

database is created automatically. nothing else to set up.

## configure

edit config.json to change settings:
- bulb_ip: your bulb IP address
- max_wattage: how much power the bulb uses max
- price_thresholds: when to show high/low price warnings
- api_refresh_interval: how often to check prices in seconds

## how to run

```bash
cd src
python dashboard.py
```

press ctrl+c to stop. your session data stays in the database.

## what you see

the dashboard shows:
- current price per MWh
- tariff level: VYSOKÝ TARIF (expensive), BĚŽNÝ PROVOZ (normal), NÍZKÝ TARIF (cheap)
- if bulb is on or off
- total energy used
- total money spent

the app checks the bulb every 2 seconds. gets new prices every 5 minutes.

## how data is stored

db.py handles saving data and has two tables:
- prices: each time we fetch a price, its stored with a timestamp
- consumption: each time bulb uses power, we save the energy and cost

when you start the app, it loads the total cost from the database. nothing gets lost if you restart.

## if something goes wrong

bulb not working? check the IP in config.json matches your bulb. make sure bulb is on your network.

API not responding? check you have internet. could be the website is down.

database broken? delete energy_data.db and restart. it will recreate though sadly hoho.

## files explained

dashboard.py - the main app, shows the interface, fetches prices and bulb data
db.py - database code, saves and loads data from SQLite
config.json - settings file
energy_data.db - where the data is stored (created on first run)

