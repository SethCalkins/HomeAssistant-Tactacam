"""Config flow for Reveal Cell Cam integration."""
import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .api import RevealCellCamAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class RevealCellCamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Reveal Cell Cam."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            try:
                # Test the credentials
                api = RevealCellCamAPI(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD]
                )
                
                # Try to authenticate
                auth_success = await api.authenticate()
                
                if auth_success:
                    # Create a unique ID for this entry
                    await self.async_set_unique_id(user_input[CONF_USERNAME])
                    self._abort_if_unique_id_configured()
                    
                    return self.async_create_entry(
                        title=f"Reveal Cell Cam ({user_input[CONF_USERNAME]})",
                        data=user_input
                    )
                else:
                    errors["base"] = "invalid_auth"
                    
                await api.close()
                
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )