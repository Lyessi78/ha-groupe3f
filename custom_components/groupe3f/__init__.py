"""The Groupe 3F integration."""
from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Groupe3FApi
from .const import (
    CONF_CONTRACT_ID, CONF_PASSWORD, CONF_TOKEN,
    CONF_TRUSTED_ID, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    contract_id = entry.data[CONF_CONTRACT_ID]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    session = async_get_clientsession(hass)
    client = Groupe3FApi(session)
    # Restore state
    client.set_credentials(entry.data.get(CONF_TOKEN), entry.data.get(CONF_TRUSTED_ID))

    async def async_update_data():
        """Fetch data with auto-reauth logic."""
        try:
            return await client.get_water_consumption(contract_id)
        except Exception:
            _LOGGER.debug("Token expired, attempting silent re-login")
            try:
                # Login silently using saved trusted_id (should bypass 2FA)
                res = await client.login(username, password)
                if res["status"] == "success":
                    new_token = res["data"]["token"]
                    hass.config_entries.async_update_entry(
                        entry, data={**entry.data, CONF_TOKEN: new_token}
                    )
                    return await client.get_water_consumption(contract_id)
                else:
                    raise UpdateFailed("Re-login required 2FA interaction")
            except Exception as err:
                raise UpdateFailed(f"API Error: {err}")

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok