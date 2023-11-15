from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.storage import STORAGE_DIR
from urllib.parse import quote
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .manifest import manifest
from .http_api import fetch_data

DOMAIN = manifest.domain

class SimpleConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 3

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors = {}
        if user_input is not None:
            url = user_input.get(CONF_URL).strip('/')
            # 检查接口是否可用
            try:
                res =  await fetch_data(f'{url}/login/status')
                if res['data']['code'] == 200:
                    user_input[CONF_URL] = url
                    return self.async_create_entry(title=DOMAIN, data=user_input)
            except Exception as ex:
                print(ex)
                errors = { 'base': 'api_failed' }
        else:
            user_input = {}

        DATA_SCHEMA = vol.Schema({
            vol.Required(CONF_URL, default=user_input.get(CONF_URL)): str
        })
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry):
        return OptionsFlowHandler(entry)

class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        options = self.config_entry.options
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title='', data=user_input)
        
        media_states = self.hass.states.async_all('media_player')
        media_entities = []

        for state in media_states:
            friendly_name = state.attributes.get('friendly_name')
            platform = state.attributes.get('platform')
            entity_id = state.entity_id
            value = f'{friendly_name}（{entity_id}）'

            if platform != 'cloud_music':
                media_entities.append({ 'label': value, 'value': entity_id })

        DATA_SCHEMA = vol.Schema({
            vol.Required('media_player', default=options.get('media_player')): selector({
                "select": {
                    "options": media_entities,
                    "multiple": True
                }
            })            
        })
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)
        