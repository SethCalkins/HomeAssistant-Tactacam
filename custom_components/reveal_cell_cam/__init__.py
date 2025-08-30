"""The Reveal Cell Cam integration."""
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import RevealCellCamAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.SENSOR, Platform.BINARY_SENSOR]
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Reveal Cell Cam from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = RevealCellCamAPI(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=api.async_get_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _register_services(hass, entry)

    return True


async def _register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register services for the integration."""
    api: RevealCellCamAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    
    async def handle_set_motion_sensitivity(call: ServiceCall) -> None:
        """Handle set motion sensitivity service call."""
        entity_id = call.data.get("entity_id")
        level = int(call.data.get("level", 5))
        
        # Extract camera ID from entity ID
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_motion_sensitivity(camera_id, level)
            if success:
                # Trigger coordinator refresh
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set motion sensitivity for camera %s", camera_id)
    
    async def handle_set_camera_mode(call: ServiceCall) -> None:
        """Handle set camera mode service call."""
        entity_id = call.data.get("entity_id")
        mode = call.data.get("mode", "photo_video")
        
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_camera_mode(camera_id, mode)
            if success:
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
    
    async def handle_set_video_length(call: ServiceCall) -> None:
        """Handle set video length service call."""
        entity_id = call.data.get("entity_id")
        length = int(call.data.get("length", 30))
        
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_video_length(camera_id, length)
            if success:
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
    
    # Register services
    hass.services.async_register(
        DOMAIN, 
        "set_motion_sensitivity", 
        handle_set_motion_sensitivity
    )
    
    hass.services.async_register(
        DOMAIN,
        "set_camera_mode",
        handle_set_camera_mode
    )
    
    hass.services.async_register(
        DOMAIN,
        "set_video_length",
        handle_set_video_length
    )
    
    async def handle_request_photo(call: ServiceCall) -> None:
        """Handle request photo service call."""
        entity_id = call.data.get("entity_id")
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.request_photo(camera_id)
            if not success:
                _LOGGER.error("Failed to request photo from camera %s", camera_id)
    
    async def handle_request_video(call: ServiceCall) -> None:
        """Handle request video service call."""
        entity_id = call.data.get("entity_id")
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.request_video(camera_id)
            if not success:
                _LOGGER.error("Failed to request video from camera %s", camera_id)
    
    hass.services.async_register(DOMAIN, "request_photo", handle_request_photo)
    hass.services.async_register(DOMAIN, "request_video", handle_request_video)
    
    # New control services
    async def handle_set_night_mode(call: ServiceCall) -> None:
        """Handle set night mode service call."""
        entity_id = call.data.get("entity_id")
        mode = call.data.get("mode", "min_blur")
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_night_mode(camera_id, mode)
            if success:
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
    
    async def handle_set_flash_type(call: ServiceCall) -> None:
        """Handle set flash type service call."""
        entity_id = call.data.get("entity_id")
        flash_type = call.data.get("type", "low_glow")
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_flash_type(camera_id, flash_type)
            if success:
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
    
    async def handle_set_multi_shot(call: ServiceCall) -> None:
        """Handle set multi-shot service call."""
        entity_id = call.data.get("entity_id")
        count = int(call.data.get("count", 1))
        interval = int(call.data.get("interval", 1))
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_multi_shot(camera_id, count, interval)
            if success:
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
    
    async def handle_set_image_resolution(call: ServiceCall) -> None:
        """Handle set image resolution service call."""
        entity_id = call.data.get("entity_id")
        resolution = call.data.get("resolution", "4k")
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_image_resolution(camera_id, resolution)
            if success:
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
    
    async def handle_set_video_resolution(call: ServiceCall) -> None:
        """Handle set video resolution service call."""
        entity_id = call.data.get("entity_id")
        resolution = call.data.get("resolution", "1080p")
        camera_id = _get_camera_id_from_entity(hass, entity_id)
        if camera_id:
            success = await api.set_video_resolution(camera_id, resolution)
            if success:
                coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
                await coordinator.async_request_refresh()
    
    hass.services.async_register(DOMAIN, "set_night_mode", handle_set_night_mode)
    hass.services.async_register(DOMAIN, "set_flash_type", handle_set_flash_type)
    hass.services.async_register(DOMAIN, "set_multi_shot", handle_set_multi_shot)
    hass.services.async_register(DOMAIN, "set_image_resolution", handle_set_image_resolution)
    hass.services.async_register(DOMAIN, "set_video_resolution", handle_set_video_resolution)


def _get_camera_id_from_entity(hass: HomeAssistant, entity_id: str) -> str | None:
    """Extract camera ID from entity ID."""
    # Entity ID format: camera.reveal_<camera_id>
    if entity_id and entity_id.startswith("camera.reveal_"):
        return entity_id.replace("camera.reveal_", "")
    return None


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unregister services
    hass.services.async_remove(DOMAIN, "set_motion_sensitivity")
    hass.services.async_remove(DOMAIN, "set_camera_mode")
    hass.services.async_remove(DOMAIN, "set_video_length")
    hass.services.async_remove(DOMAIN, "request_photo")
    hass.services.async_remove(DOMAIN, "request_video")
    hass.services.async_remove(DOMAIN, "set_night_mode")
    hass.services.async_remove(DOMAIN, "set_flash_type")
    hass.services.async_remove(DOMAIN, "set_multi_shot")
    hass.services.async_remove(DOMAIN, "set_image_resolution")
    hass.services.async_remove(DOMAIN, "set_video_resolution")
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok