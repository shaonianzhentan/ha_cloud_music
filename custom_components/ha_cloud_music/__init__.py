from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_URL

from .const import PLATFORMS
from .manifest import manifest
from .http import HttpView
from .cloud_music import CloudMusic

DOMAIN = manifest.domain

CONFIG_SCHEMA = cv.deprecated(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    data = entry.data
    api_url = data.get(CONF_URL)
    hass.data['cloud_music'] = CloudMusic(hass, api_url)

    hass.http.register_view(HttpView)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass, entry):
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)