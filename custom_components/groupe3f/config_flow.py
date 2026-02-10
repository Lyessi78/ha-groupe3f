"""Config flow for Groupe 3F."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Groupe3FApi
from .const import CONF_CONTRACT_ID, CONF_TOKEN, CONF_TRUSTED_ID, DOMAIN, CONF_PRICE

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._username = None
        self._password = None
        self._price = 0.0
        self._api = None

    async def _finish_setup(self, token: str) -> config_entries.ConfigFlowResult:
        """Fetch contract and create entry."""
        try:
            # Ensure API has credentials set for subsequent calls
            self._api.set_credentials(token, self._api.get_trusted_id())
            # We need to set username for get_caint_num to work
            self._api._username = self._username
            
            contract_id = await self._api.get_contract_id()
            await self.async_set_unique_id(contract_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Contrat {contract_id}",
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_CONTRACT_ID: contract_id,
                    CONF_TOKEN: token,
                    CONF_TRUSTED_ID: self._api.get_trusted_id(),
                    CONF_PRICE: self._price,
                },
            )
        except Exception:
            _LOGGER.exception("Error finishing setup")
            return self.async_abort(reason="no_contracts")

    async def async_step_user(self, user_input=None):
        """Step 1: Credentials."""
        errors = {}
        if user_input:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._price = user_input.get(CONF_PRICE, 0.0)
            session = async_get_clientsession(self.hass)
            self._api = Groupe3FApi(session)

            try:
                result = await self._api.login(self._username, self._password)
                if result["status"] == "success":
                    return await self._finish_setup(result["data"]["token"])
                elif result["status"] == "2fa_required":
                    return await self.async_step_2fa()
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_PRICE, default=0.0): vol.Coerce(float),
            }),
            errors=errors
        )

    async def async_step_2fa(self, user_input=None):
        """Step 2: 2FA Code."""
        errors = {}
        if user_input:
            try:
                # Re-init API if lost context (should not happen usually but safe)
                if not self._api:
                    session = async_get_clientsession(self.hass)
                    self._api = Groupe3FApi(session)
                    # Restore trusted_id if possible, but here we are in flow context
                    # Ideally we should persist it in flow state if needed

                result = await self._api.check_2fa(user_input["code"])
                if result["status"] == "success":
                    return await self._finish_setup(result["data"]["token"])
            except Exception:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="2fa",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors
        )