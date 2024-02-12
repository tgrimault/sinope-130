from homeassistant.const import UnitOfTemperature

HA_TO_NEVIWEB_PERIOD = {
    "15 sec": 15,
    "5 min": 300,
    "10 min": 600,
    "15 min": 900,
    "20 min": 1200,
    "25 min": 1500,
    "30 min": 1800
}


def neviweb_to_ha(value):
    keys = [k for k, v in HA_TO_NEVIWEB_PERIOD.items() if v == value]
    if keys:
        return keys[0]
    return None


def temp_format_to_ha(value):
    if value == "celsius":
        return UnitOfTemperature.CELSIUS
    else:
        return UnitOfTemperature.FAHRENHEIT


def lock_to_ha(lock):
    """Convert keypad lock state to better description."""
    match lock:
        case "locked":
            return "Locked"
        case "lock":
            return "Locked"
        case "unlocked":
            return "Unlocked"
        case "unlock":
            return "Unlocked"
        case "partiallyLocked":
            return "Tamper protection"
        case "partialLock":
            return "Tamper protection"