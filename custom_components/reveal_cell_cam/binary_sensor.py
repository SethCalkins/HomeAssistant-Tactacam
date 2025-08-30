"""Binary sensor platform for Reveal Cell Cam."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Reveal Cell Cam binary sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    sensors = []
    if coordinator.data and "cameras" in coordinator.data:
        for camera in coordinator.data["cameras"]:
            camera_id = camera.get("cameraId")
            # Try multiple fields for camera name
            camera_name = camera.get("cameraName") or camera.get("cameraLocation") or camera.get("name") or f"Camera {camera_id[-4:]}"
            
            # Create binary sensors for each camera
            sensors.extend([
                RevealExternalPowerSensor(coordinator, camera_id, camera_name),
                RevealCameraOnlineSensor(coordinator, camera_id, camera_name),
            ])
    
    async_add_entities(sensors)


class RevealBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Reveal Cell Cam binary sensors."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        camera_id: str,
        camera_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._sensor_type = sensor_type
        self._attr_unique_id = f"reveal_{camera_id}_{sensor_type}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, camera_id)},
            "name": camera_name,
            "manufacturer": "Tactacam",
            "model": "Reveal Cell Cam",
        }

    def _get_camera_data(self) -> Dict[str, Any]:
        """Get camera data from coordinator."""
        if not self.coordinator.data or "cameras" not in self.coordinator.data:
            return {}
        
        for camera in self.coordinator.data["cameras"]:
            if camera.get("cameraId") == self._camera_id:
                return camera
        
        return {}


class RevealExternalPowerSensor(RevealBinarySensorBase):
    """External power connected binary sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the external power sensor."""
        super().__init__(coordinator, camera_id, camera_name, "external_power")
        self._attr_name = "External Power"
        self._attr_device_class = BinarySensorDeviceClass.PLUG
        self._attr_icon = "mdi:power-plug"

    @property
    def is_on(self) -> bool:
        """Return true if external power is connected."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            
            # Check voltage source - "Backup" means on battery, anything else is external
            voltage_source = status.get("voltagesource")
            if voltage_source and voltage_source != "Backup":
                return True
            
            # Also check external voltage value
            voltage_external = status.get("voltageexternal")
            if voltage_external:
                try:
                    # Remove 'v' or 'V' and convert to float
                    voltage_str = str(voltage_external).lower().replace("v", "").strip()
                    voltage = float(voltage_str)
                    # If external voltage is greater than 0, power is connected
                    return voltage > 0.5  # Use 0.5V threshold to avoid noise
                except (ValueError, TypeError):
                    pass
        
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            
            if "voltagesource" in status:
                attrs["power_source"] = status["voltagesource"]
            
            if "voltageexternal" in status:
                attrs["external_voltage"] = status["voltageexternal"]
            
            if "voltageinternal" in status:
                attrs["battery_voltage"] = status["voltageinternal"]
        
        return attrs


class RevealCameraOnlineSensor(RevealBinarySensorBase):
    """Camera online binary sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the camera online sensor."""
        super().__init__(coordinator, camera_id, camera_name, "camera_online")
        self._attr_name = "Camera Online"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:camera-wireless"

    @property
    def is_on(self) -> bool:
        """Return true if camera is online (transmitted recently)."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            last_transmission = status.get("lastTransmissionTimestamp")
            
            if last_transmission is not None:
                try:
                    # Convert milliseconds timestamp to datetime
                    last_transmission_dt = datetime.fromtimestamp(last_transmission / 1000, tz=dt_util.UTC)
                    current_time = dt_util.utcnow()
                    
                    # Consider camera online if transmitted within last 24 hours
                    time_since_transmission = current_time - last_transmission_dt
                    return time_since_transmission < timedelta(hours=24)
                except (ValueError, TypeError, OSError):
                    pass
        
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            
            if "lastTransmissionTimestamp" in status:
                try:
                    timestamp = status["lastTransmissionTimestamp"]
                    last_transmission_dt = datetime.fromtimestamp(timestamp / 1000, tz=dt_util.UTC)
                    attrs["last_transmission"] = last_transmission_dt.isoformat()
                    
                    # Calculate time since last transmission
                    current_time = dt_util.utcnow()
                    time_since = current_time - last_transmission_dt
                    
                    if time_since.total_seconds() > 0:
                        days = time_since.days
                        hours = time_since.seconds // 3600
                        minutes = (time_since.seconds % 3600) // 60
                        attrs["time_since_transmission"] = f"{days}d {hours}h {minutes}m"
                        
                        # Add status based on time
                        if time_since < timedelta(hours=1):
                            attrs["connection_status"] = "Recently Active"
                        elif time_since < timedelta(hours=12):
                            attrs["connection_status"] = "Active Today"
                        elif time_since < timedelta(hours=24):
                            attrs["connection_status"] = "Active Yesterday"
                        elif time_since < timedelta(days=7):
                            attrs["connection_status"] = "Active This Week"
                        else:
                            attrs["connection_status"] = "Inactive"
                except (ValueError, TypeError, OSError):
                    pass
            
            # Add signal strength if available
            if "signal" in status:
                attrs["signal_strength"] = f"{status['signal']}/5"
        
        return attrs