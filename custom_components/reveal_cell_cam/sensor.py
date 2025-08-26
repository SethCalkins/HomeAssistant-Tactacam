"""Sensor platform for Reveal Cell Cam."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
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
    """Set up the Reveal Cell Cam sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    sensors = []
    if coordinator.data and "cameras" in coordinator.data:
        for camera in coordinator.data["cameras"]:
            camera_id = camera.get("cameraId")
            camera_name = camera.get("cameraName", "Unknown")
            
            # Create sensors for each camera
            sensors.extend([
                RevealBatterySensor(coordinator, camera_id, camera_name),
                RevealSignalSensor(coordinator, camera_id, camera_name),
                RevealTemperatureSensor(coordinator, camera_id, camera_name),
                RevealPhotoCountSensor(coordinator, camera_id, camera_name),
                RevealWindSpeedSensor(coordinator, camera_id, camera_name),
                RevealPressureSensor(coordinator, camera_id, camera_name),
                RevealMoonPhaseSensor(coordinator, camera_id, camera_name),
                RevealWeatherSensor(coordinator, camera_id, camera_name),
                RevealLastPhotoSensor(coordinator, camera_id, camera_name),
            ])
    
    async_add_entities(sensors)


class RevealSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Reveal Cell Cam sensors."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        camera_id: str,
        camera_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._sensor_type = sensor_type
        self._attr_unique_id = f"reveal_{camera_id}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, camera_id)},
            "name": f"Reveal {camera_name}",
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

    def _get_latest_photo(self) -> Dict[str, Any]:
        """Get latest photo data."""
        camera_data = self._get_camera_data()
        return camera_data.get("latest_photo", {})


class RevealBatterySensor(RevealSensorBase):
    """Battery level sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, camera_id, camera_name, "battery")
        self._attr_name = f"{camera_name} Battery"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the battery level."""
        photo = self._get_latest_photo()
        if photo and "metadata" in photo:
            battery = photo["metadata"].get("batteryLevel")
            if battery is not None:
                try:
                    return int(battery)
                except (ValueError, TypeError):
                    pass
        
        # Fall back to stats
        camera_data = self._get_camera_data()
        if "stats" in camera_data:
            return camera_data["stats"].get("current_battery")
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        camera_data = self._get_camera_data()
        attrs = {}
        
        if "stats" in camera_data:
            if "average_battery" in camera_data["stats"]:
                attrs["average"] = camera_data["stats"]["average_battery"]
        
        return attrs


class RevealSignalSensor(RevealSensorBase):
    """Signal strength sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the signal sensor."""
        super().__init__(coordinator, camera_id, camera_name, "signal")
        self._attr_name = f"{camera_name} Signal"
        self._attr_icon = "mdi:signal"

    @property
    def native_value(self) -> Optional[str]:
        """Return the signal strength."""
        photo = self._get_latest_photo()
        if photo and "metadata" in photo:
            signal = photo["metadata"].get("signal")
            if signal is not None:
                return f"{signal}/5"
        
        # Fall back to stats
        camera_data = self._get_camera_data()
        if "stats" in camera_data:
            signal = camera_data["stats"].get("current_signal")
            if signal:
                return f"{signal}/5"
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        camera_data = self._get_camera_data()
        attrs = {}
        
        if "stats" in camera_data:
            if "average_signal" in camera_data["stats"]:
                attrs["average"] = f"{camera_data['stats']['average_signal']:.1f}/5"
        
        photo = self._get_latest_photo()
        if photo and "metadata" in photo:
            if "signal" in photo["metadata"]:
                try:
                    signal_val = int(photo["metadata"]["signal"])
                    attrs["signal_bars"] = signal_val
                    attrs["signal_quality"] = ["No Signal", "Poor", "Fair", "Good", "Very Good", "Excellent"][min(signal_val, 5)]
                except (ValueError, TypeError, IndexError):
                    pass
        
        return attrs


class RevealTemperatureSensor(RevealSensorBase):
    """Temperature sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, camera_id, camera_name, "temperature")
        self._attr_name = f"{camera_name} Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the temperature."""
        photo = self._get_latest_photo()
        if photo and "weatherData" in photo:
            temp = photo["weatherData"].get("currentTemp")
            if temp is not None:
                try:
                    return float(temp)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        photo = self._get_latest_photo()
        
        if photo and "weatherData" in photo:
            weather = photo["weatherData"]
            if "tempMin12hr" in weather:
                attrs["12hr_min"] = weather["tempMin12hr"]
            if "tempMax12hr" in weather:
                attrs["12hr_max"] = weather["tempMax12hr"]
            if "tempDepature24hr" in weather:
                attrs["24hr_departure"] = weather["tempDepature24hr"]
        
        return attrs


class RevealPhotoCountSensor(RevealSensorBase):
    """Photo count sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the photo count sensor."""
        super().__init__(coordinator, camera_id, camera_name, "photo_count")
        self._attr_name = f"{camera_name} Photo Count"
        self._attr_icon = "mdi:camera"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> Optional[int]:
        """Return the photo count."""
        camera_data = self._get_camera_data()
        
        if "stats" in camera_data:
            count = camera_data["stats"].get("total_photos")
            if count is not None:
                return count
        
        # Fall back to count from camera data
        return camera_data.get("photoCount", 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "stats" in camera_data:
            stats = camera_data["stats"]
            if "first_photo_date" in stats:
                attrs["first_photo"] = stats["first_photo_date"]
            if "last_photo_date" in stats:
                attrs["last_photo"] = stats["last_photo_date"]
        
        return attrs


class RevealWindSpeedSensor(RevealSensorBase):
    """Wind speed sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the wind speed sensor."""
        super().__init__(coordinator, camera_id, camera_name, "wind_speed")
        self._attr_name = f"{camera_name} Wind Speed"
        self._attr_native_unit_of_measurement = UnitOfSpeed.MILES_PER_HOUR
        self._attr_device_class = SensorDeviceClass.WIND_SPEED
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the wind speed."""
        photo = self._get_latest_photo()
        if photo and "weatherData" in photo:
            speed = photo["weatherData"].get("windSpeed")
            if speed is not None:
                try:
                    return float(speed)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        photo = self._get_latest_photo()
        
        if photo and "weatherData" in photo:
            weather = photo["weatherData"]
            if "windDirection" in weather:
                attrs["direction"] = weather["windDirection"]
            if "windGust" in weather:
                attrs["gust_speed"] = weather["windGust"]
        
        return attrs


class RevealPressureSensor(RevealSensorBase):
    """Barometric pressure sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the pressure sensor."""
        super().__init__(coordinator, camera_id, camera_name, "pressure")
        self._attr_name = f"{camera_name} Pressure"
        self._attr_native_unit_of_measurement = UnitOfPressure.INHG
        self._attr_device_class = SensorDeviceClass.ATMOSPHERIC_PRESSURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the barometric pressure."""
        photo = self._get_latest_photo()
        if photo and "weatherData" in photo:
            pressure = photo["weatherData"].get("barometricPressure")
            if pressure is not None:
                try:
                    return float(pressure)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        photo = self._get_latest_photo()
        
        if photo and "weatherData" in photo:
            weather = photo["weatherData"]
            if "pressureTendency" in weather:
                attrs["tendency"] = weather["pressureTendency"]
        
        return attrs


class RevealMoonPhaseSensor(RevealSensorBase):
    """Moon phase sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the moon phase sensor."""
        super().__init__(coordinator, camera_id, camera_name, "moon_phase")
        self._attr_name = f"{camera_name} Moon Phase"
        self._attr_icon = "mdi:moon-waxing-crescent"

    @property
    def native_value(self) -> Optional[str]:
        """Return the moon phase."""
        photo = self._get_latest_photo()
        if photo and "weatherData" in photo:
            return photo["weatherData"].get("moonPhase")
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        photo = self._get_latest_photo()
        
        if photo and "weatherData" in photo:
            weather = photo["weatherData"]
            if "sunPhase" in weather:
                attrs["sun_phase"] = weather["sunPhase"]
        
        return attrs


class RevealWeatherSensor(RevealSensorBase):
    """Weather condition sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the weather sensor."""
        super().__init__(coordinator, camera_id, camera_name, "weather")
        self._attr_name = f"{camera_name} Weather"
        self._attr_icon = "mdi:weather-partly-cloudy"

    @property
    def native_value(self) -> Optional[str]:
        """Return the weather condition."""
        photo = self._get_latest_photo()
        if photo and "weatherData" in photo:
            return photo["weatherData"].get("weather")
        
        return None


class RevealLastPhotoSensor(RevealSensorBase):
    """Last photo time sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the last photo sensor."""
        super().__init__(coordinator, camera_id, camera_name, "last_photo")
        self._attr_name = f"{camera_name} Last Photo"
        self._attr_icon = "mdi:camera-timer"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> Optional[datetime]:
        """Return the last photo timestamp."""
        photo = self._get_latest_photo()
        if photo and "photoDateUtc" in photo:
            timestamp_str = photo.get("photoDateUtc")
            if timestamp_str:
                try:
                    # Parse ISO format timestamp
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1] + '+00:00'
                    return datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError) as err:
                    _LOGGER.debug("Failed to parse timestamp %s: %s", timestamp_str, err)
                    return None
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        photo = self._get_latest_photo()
        
        if photo:
            if "photoName" in photo:
                attrs["filename"] = photo["photoName"]
            if "metadata" in photo and "gpsLatitude" in photo["metadata"]:
                attrs["gps_location"] = f"{photo['metadata'].get('gpsLatitude')}, {photo['metadata'].get('gpsLongitude')}"
        
        return attrs