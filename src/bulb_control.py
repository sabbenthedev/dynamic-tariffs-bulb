import asyncio

from pywizlight import PilotBuilder, wizlight

bulb_ip = "192.168.0.46"


async def test_bulb():
    light = wizlight(bulb_ip)
    print(f"Připojuji se k žárovce na {bulb_ip}...")

    try:
        # green color (RGB: 0, 255, 0)
        print("Měním barvu na zelenou...")
        await light.turn_on(PilotBuilder(rgb=(0, 255, 0)))
        await asyncio.sleep(3)

        # red color (RGB: 255, 0, 0)
        print("Měním barvu na červenou...")
        await light.turn_on(PilotBuilder(rgb=(255, 0, 0)))
        await asyncio.sleep(3)

        # returning to normal light
        print("Vracím na bílou...")
        await light.turn_on(PilotBuilder(cold_white=255))

    except Exception as e:
        print(f"Chyba při komunikaci se žárovkou: {e}")


if __name__ == "__main__":
    asyncio.run(test_bulb())
