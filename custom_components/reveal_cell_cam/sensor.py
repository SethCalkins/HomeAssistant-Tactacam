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
    UnitOfTime,
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
            # Try multiple fields for camera name
            camera_name = camera.get("cameraName") or camera.get("cameraLocation") or camera.get("name") or f"Camera {camera_id[-4:]}"
            
            # Create sensors for each camera
            sensors.extend([
                RevealBatterySensor(coordinator, camera_id, camera_name),
                RevealSignalSensor(coordinator, camera_id, camera_name),
                RevealTemperatureSensor(coordinator, camera_id, camera_name),
                RevealPhotoCountSensor(coordinator, camera_id, camera_name),
                RevealWindSpeedSensor(coordinator, camera_id, camera_name),
                RevealWindDirectionSensor(coordinator, camera_id, camera_name),
                RevealPressureSensor(coordinator, camera_id, camera_name),
                RevealMoonPhaseSensor(coordinator, camera_id, camera_name),
                RevealWeatherSensor(coordinator, camera_id, camera_name),
                RevealLastPhotoSensor(coordinator, camera_id, camera_name),
                RevealSDCardUsageSensor(coordinator, camera_id, camera_name),
                RevealCameraUptimeSensor(coordinator, camera_id, camera_name),
                RevealGPSCoordinatesSensor(coordinator, camera_id, camera_name),
                RevealSIMCarrierSensor(coordinator, camera_id, camera_name),
                RevealInternalVoltageSensor(coordinator, camera_id, camera_name),
                RevealExternalVoltageSensor(coordinator, camera_id, camera_name),
                RevealFirmwareVersionSensor(coordinator, camera_id, camera_name),
                RevealCameraTemperatureSensor(coordinator, camera_id, camera_name),
                RevealServingCellSensor(coordinator, camera_id, camera_name),
                RevealCameraSettingsSensor(coordinator, camera_id, camera_name),
                RevealPhotosTakenSensor(coordinator, camera_id, camera_name),
                RevealStoredPhotosSensor(coordinator, camera_id, camera_name),
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
        self._attr_name = "Battery"
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
        self._attr_name = "Signal"
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
        self._attr_name = "Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the temperature."""
        photo = self._get_latest_photo()
        
        # Try different field names for weather data
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            # Try different field names for temperature
            temp = weather_data.get("currentTemp") or weather_data.get("temperature") or weather_data.get("temp")
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
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            # Try different field names for temperature range
            if "tempMin12hr" in weather_data:
                attrs["12hr_min"] = weather_data["tempMin12hr"]
            elif "temperatureRange12Hours" in weather_data:
                temp_range = weather_data["temperatureRange12Hours"]
                if "min" in temp_range:
                    attrs["12hr_min"] = temp_range["min"]
                if "max" in temp_range:
                    attrs["12hr_max"] = temp_range["max"]
            
            if "tempMax12hr" in weather_data:
                attrs["12hr_max"] = weather_data["tempMax12hr"]
            
            if "tempDepature24hr" in weather_data:
                attrs["24hr_departure"] = weather_data["tempDepature24hr"]
            elif "past24HoursTemperatureDeparture" in weather_data:
                attrs["24hr_departure"] = weather_data["past24HoursTemperatureDeparture"]
        
        return attrs


class RevealPhotoCountSensor(RevealSensorBase):
    """Photo count sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the photo count sensor."""
        super().__init__(coordinator, camera_id, camera_name, "photo_count")
        self._attr_name = "Photo Count"
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
        self._attr_name = "Wind Speed"
        self._attr_native_unit_of_measurement = UnitOfSpeed.MILES_PER_HOUR
        self._attr_device_class = SensorDeviceClass.WIND_SPEED
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the wind speed."""
        photo = self._get_latest_photo()
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            # Try direct windSpeed field
            speed = weather_data.get("windSpeed")
            if speed is not None:
                try:
                    return float(speed)
                except (ValueError, TypeError):
                    pass
            
            # Try windDirection object
            wind_dir = weather_data.get("windDirection")
            if wind_dir and isinstance(wind_dir, dict):
                speed = wind_dir.get("speed")
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
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            # Handle wind direction as string or object
            wind_dir = weather_data.get("windDirection")
            if wind_dir:
                if isinstance(wind_dir, dict):
                    attrs["direction"] = wind_dir.get("cardinalLabel") or wind_dir.get("direction")
                else:
                    attrs["direction"] = wind_dir
            
            if "windGust" in weather_data:
                attrs["gust_speed"] = weather_data["windGust"]
        
        return attrs


class RevealWindDirectionSensor(RevealSensorBase):
    """Wind direction sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the wind direction sensor."""
        super().__init__(coordinator, camera_id, camera_name, "wind_direction")
        self._attr_name = "Wind Direction"
        self._attr_icon = "mdi:compass"

    @property
    def native_value(self) -> Optional[str]:
        """Return the wind direction."""
        photo = self._get_latest_photo()
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            # Handle wind direction as string or object
            wind_dir = weather_data.get("windDirection")
            if wind_dir:
                if isinstance(wind_dir, dict):
                    # If it's an object, get the cardinal direction
                    return wind_dir.get("cardinalLabel") or wind_dir.get("direction")
                else:
                    # If it's a string, return it directly
                    return wind_dir
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        photo = self._get_latest_photo()
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            wind_dir = weather_data.get("windDirection")
            if wind_dir and isinstance(wind_dir, dict):
                # If wind direction is an object, extract all available data
                if "degrees" in wind_dir:
                    attrs["degrees"] = wind_dir["degrees"]
                if "speed" in wind_dir:
                    attrs["wind_speed"] = wind_dir["speed"]
                if "cardinalLabel" in wind_dir:
                    attrs["cardinal"] = wind_dir["cardinalLabel"]
                elif "direction" in wind_dir:
                    attrs["cardinal"] = wind_dir["direction"]
            
            # Also check for wind speed if available separately
            if "windSpeed" in weather_data:
                attrs["wind_speed"] = weather_data["windSpeed"]
            
            # Add wind gust if available
            if "windGust" in weather_data:
                attrs["wind_gust"] = weather_data["windGust"]
        
        return attrs


class RevealPressureSensor(RevealSensorBase):
    """Barometric pressure sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the pressure sensor."""
        super().__init__(coordinator, camera_id, camera_name, "pressure")
        self._attr_name = "Pressure"
        self._attr_native_unit_of_measurement = UnitOfPressure.INHG
        self._attr_device_class = SensorDeviceClass.ATMOSPHERIC_PRESSURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the barometric pressure."""
        photo = self._get_latest_photo()
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            pressure = weather_data.get("barometricPressure") or weather_data.get("pressure")
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
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            if "pressureTendency" in weather_data:
                attrs["tendency"] = weather_data["pressureTendency"]
        
        return attrs


class RevealMoonPhaseSensor(RevealSensorBase):
    """Moon phase sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the moon phase sensor."""
        super().__init__(coordinator, camera_id, camera_name, "moon_phase")
        self._attr_name = "Moon Phase"
        self._attr_icon = "mdi:moon-waxing-crescent"

    @property
    def native_value(self) -> Optional[str]:
        """Return the moon phase."""
        photo = self._get_latest_photo()
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            return weather_data.get("moonPhase") or weather_data.get("moon_phase")
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        photo = self._get_latest_photo()
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            if "sunPhase" in weather_data:
                attrs["sun_phase"] = weather_data["sunPhase"]
            elif "sun_phase" in weather_data:
                attrs["sun_phase"] = weather_data["sun_phase"]
        
        return attrs


class RevealWeatherSensor(RevealSensorBase):
    """Weather condition sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the weather sensor."""
        super().__init__(coordinator, camera_id, camera_name, "weather")
        self._attr_name = "Weather"
        self._attr_icon = "mdi:weather-partly-cloudy"

    @property
    def native_value(self) -> Optional[str]:
        """Return the weather condition."""
        photo = self._get_latest_photo()
        
        weather_data = None
        if photo:
            weather_data = photo.get("weatherData") or photo.get("weatherRecord") or photo.get("weather")
        
        if weather_data:
            return weather_data.get("weather") or weather_data.get("weatherLabel") or weather_data.get("conditions")
        
        return None


class RevealLastPhotoSensor(RevealSensorBase):
    """Last photo time sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the last photo sensor."""
        super().__init__(coordinator, camera_id, camera_name, "last_photo")
        self._attr_name = "Last Photo"
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


class RevealSDCardUsageSensor(RevealSensorBase):
    """SD Card usage sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the SD card usage sensor."""
        super().__init__(coordinator, camera_id, camera_name, "sd_card_usage")
        self._attr_name = "SD Card Usage"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:micro-sd"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the SD card usage percentage."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            memory = status.get("memory")
            memory_limit = status.get("memoryLimit")
            
            if memory is not None and memory_limit is not None and memory_limit > 0:
                try:
                    usage_percent = (float(memory) / float(memory_limit)) * 100
                    return round(usage_percent, 1)
                except (ValueError, TypeError, ZeroDivisionError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            if "memory" in status:
                attrs["used_mb"] = status["memory"]
            if "memoryLimit" in status:
                attrs["total_mb"] = status["memoryLimit"]
            
            memory = status.get("memory")
            memory_limit = status.get("memoryLimit")
            if memory is not None and memory_limit is not None:
                attrs["free_mb"] = memory_limit - memory
        
        return attrs


class RevealCameraUptimeSensor(RevealSensorBase):
    """Camera uptime sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the camera uptime sensor."""
        super().__init__(coordinator, camera_id, camera_name, "camera_uptime")
        self._attr_name = "Camera Uptime"
        self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        self._attr_icon = "mdi:timer-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the camera uptime in hours."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            last_transmission = status.get("lastTransmissionTimestamp")
            
            if last_transmission is not None:
                try:
                    # Convert milliseconds timestamp to datetime
                    last_transmission_dt = datetime.fromtimestamp(last_transmission / 1000, tz=dt_util.UTC)
                    current_time = dt_util.utcnow()
                    
                    # Calculate uptime in hours
                    uptime_delta = current_time - last_transmission_dt
                    uptime_hours = uptime_delta.total_seconds() / 3600
                    
                    # If uptime is negative or very large, return None
                    if uptime_hours < 0 or uptime_hours > 8760:  # More than a year
                        return None
                    
                    return round(uptime_hours, 2)
                except (ValueError, TypeError, OSError):
                    pass
        
        return None

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
                    
                    # Calculate days, hours, minutes
                    current_time = dt_util.utcnow()
                    uptime_delta = current_time - last_transmission_dt
                    
                    if uptime_delta.total_seconds() > 0:
                        days = uptime_delta.days
                        hours = uptime_delta.seconds // 3600
                        minutes = (uptime_delta.seconds % 3600) // 60
                        attrs["uptime_formatted"] = f"{days}d {hours}h {minutes}m"
                except (ValueError, TypeError, OSError):
                    pass
        
        return attrs


class RevealGPSCoordinatesSensor(RevealSensorBase):
    """GPS coordinates sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the GPS coordinates sensor."""
        super().__init__(coordinator, camera_id, camera_name, "gps_coordinates")
        self._attr_name = "GPS Coordinates"
        self._attr_icon = "mdi:map-marker"

    @property
    def native_value(self) -> Optional[str]:
        """Return the GPS coordinates."""
        camera_data = self._get_camera_data()
        
        if "gps" in camera_data:
            gps = camera_data["gps"]
            latitude = gps.get("latitude")
            longitude = gps.get("longitude")
            
            if latitude is not None and longitude is not None:
                try:
                    lat = float(latitude)
                    lon = float(longitude)
                    return f"{lat:.5f}, {lon:.5f}"
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "gps" in camera_data:
            gps = camera_data["gps"]
            
            if "latitude" in gps:
                try:
                    attrs["latitude"] = float(gps["latitude"])
                except (ValueError, TypeError):
                    attrs["latitude"] = gps["latitude"]
            
            if "longitude" in gps:
                try:
                    attrs["longitude"] = float(gps["longitude"])
                except (ValueError, TypeError):
                    attrs["longitude"] = gps["longitude"]
            
            if "lastUpdatedTimestamp" in gps:
                attrs["last_gps_update"] = gps["lastUpdatedTimestamp"]
            
            # Add Google Maps link
            if "latitude" in attrs and "longitude" in attrs:
                lat = attrs["latitude"]
                lon = attrs["longitude"]
                attrs["google_maps_link"] = f"https://maps.google.com/?q={lat},{lon}"
        
        return attrs


class RevealSIMCarrierSensor(RevealSensorBase):
    """SIM carrier sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the SIM carrier sensor."""
        super().__init__(coordinator, camera_id, camera_name, "sim_carrier")
        self._attr_name = "SIM Carrier"
        self._attr_icon = "mdi:sim"

    @property
    def native_value(self) -> Optional[str]:
        """Return the active SIM carrier."""
        camera_data = self._get_camera_data()
        
        # Try status.eSim array first
        if "status" in camera_data:
            status = camera_data["status"]
            esim = status.get("eSim", [])
            
            for sim in esim:
                if sim.get("activeFlag") == 1:
                    return sim.get("carrier")
        
        # Fall back to phoneCarrier field
        return camera_data.get("phoneCarrier")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            esim = status.get("eSim", [])
            
            attrs["available_carriers"] = []
            for i, sim in enumerate(esim):
                carrier = sim.get("carrier")
                if carrier:
                    attrs["available_carriers"].append(carrier)
                    if sim.get("activeFlag") == 1:
                        attrs["active_iccid"] = sim.get("iccid")
            
            # Add serving cell info
            if "servingCell" in status:
                serving_cell = status["servingCell"]
                # Parse: "FDD LTE,311480,LTE BAND 4,2350,-79,221,-15"
                parts = serving_cell.split(",")
                if len(parts) >= 7:
                    attrs["network_type"] = parts[0]
                    attrs["network_operator"] = parts[1]
                    attrs["band"] = parts[2]
                    attrs["frequency"] = f"{parts[3]} MHz"
                    attrs["rssi"] = f"{parts[4]} dBm"
        
        # Add main ICCID if available
        if "iccid" in camera_data:
            attrs["main_iccid"] = camera_data["iccid"]
        
        return attrs


class RevealInternalVoltageSensor(RevealSensorBase):
    """Internal voltage sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the internal voltage sensor."""
        super().__init__(coordinator, camera_id, camera_name, "internal_voltage")
        self._attr_name = "Internal Voltage"
        self._attr_icon = "mdi:battery-charging"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the internal voltage."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            voltage = status.get("voltageinternal")
            
            if voltage:
                try:
                    # Remove 'v' or 'V' and convert to float
                    voltage_str = str(voltage).lower().replace("v", "").strip()
                    return float(voltage_str)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            if "voltagesource" in status:
                attrs["power_source"] = status["voltagesource"]
        
        return attrs


class RevealExternalVoltageSensor(RevealSensorBase):
    """External voltage sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the external voltage sensor."""
        super().__init__(coordinator, camera_id, camera_name, "external_voltage")
        self._attr_name = "External Voltage"
        self._attr_icon = "mdi:power-plug"
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the external voltage."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            voltage = status.get("voltageexternal")
            
            if voltage:
                try:
                    # Remove 'v' or 'V' and convert to float
                    voltage_str = str(voltage).lower().replace("v", "").strip()
                    return float(voltage_str)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            if "voltagesource" in status:
                attrs["power_source"] = status["voltagesource"]
                attrs["external_power_connected"] = status["voltagesource"] != "Backup"
        
        return attrs


class RevealFirmwareVersionSensor(RevealSensorBase):
    """Firmware version sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the firmware version sensor."""
        super().__init__(coordinator, camera_id, camera_name, "firmware_version")
        self._attr_name = "Firmware Version"
        self._attr_icon = "mdi:chip"

    @property
    def native_value(self) -> Optional[str]:
        """Return the firmware version."""
        camera_data = self._get_camera_data()
        return camera_data.get("firmwareVersion")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "hardwareVersion" in camera_data:
            attrs["hardware_version"] = camera_data["hardwareVersion"]
        
        if "status" in camera_data:
            status = camera_data["status"]
            if "mcuVersion" in status:
                attrs["mcu_version"] = status["mcuVersion"]
            if "appVersion" in status:
                attrs["app_version"] = status["appVersion"]
        
        if "firmwareStatus" in camera_data:
            attrs["firmware_status"] = camera_data["firmwareStatus"]
        
        if "planTier" in camera_data:
            attrs["plan_tier"] = camera_data["planTier"]
        
        return attrs


class RevealCameraTemperatureSensor(RevealSensorBase):
    """Camera internal temperature sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the camera temperature sensor."""
        super().__init__(coordinator, camera_id, camera_name, "camera_temperature")
        self._attr_name = "Camera Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> Optional[float]:
        """Return the camera internal temperature."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            temperature = status.get("temperature")
            
            if temperature is not None:
                try:
                    return float(temperature)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            temp = status.get("temperature")
            if temp is not None:
                try:
                    celsius = float(temp)
                    fahrenheit = (celsius * 9/5) + 32
                    attrs["temperature_fahrenheit"] = round(fahrenheit, 1)
                except (ValueError, TypeError):
                    pass
        
        return attrs


class RevealServingCellSensor(RevealSensorBase):
    """Serving cell details sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the serving cell sensor."""
        super().__init__(coordinator, camera_id, camera_name, "serving_cell")
        self._attr_name = "Serving Cell"
        self._attr_icon = "mdi:antenna"

    @property
    def native_value(self) -> Optional[str]:
        """Return the serving cell network type and band."""
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            serving_cell = status.get("servingCell")
            
            if serving_cell:
                # Parse: "FDD LTE,311480,LTE BAND 4,2350,-79,221,-15"
                parts = serving_cell.split(",")
                if len(parts) >= 3:
                    network_type = parts[0]
                    band = parts[2]
                    return f"{network_type} - {band}"
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "status" in camera_data:
            status = camera_data["status"]
            serving_cell = status.get("servingCell")
            
            if serving_cell:
                # Parse: "FDD LTE,311480,LTE BAND 4,2350,-79,221,-15"
                parts = serving_cell.split(",")
                
                if len(parts) >= 7:
                    attrs["network_type"] = parts[0]
                    attrs["network_operator"] = parts[1]
                    attrs["band"] = parts[2]
                    attrs["frequency"] = f"{parts[3]} MHz"
                    attrs["rssi"] = f"{parts[4]} dBm"
                    attrs["rsrp"] = f"{parts[5]} dBm"
                    attrs["rsrq"] = f"{parts[6]} dB"
                    
                    # Add signal quality interpretation
                    try:
                        rssi = int(parts[4])
                        if rssi >= -70:
                            attrs["signal_quality"] = "Excellent"
                        elif rssi >= -85:
                            attrs["signal_quality"] = "Good"
                        elif rssi >= -100:
                            attrs["signal_quality"] = "Fair"
                        else:
                            attrs["signal_quality"] = "Poor"
                    except (ValueError, IndexError):
                        pass
                    
                    # Add operator name mapping for common US carriers
                    operator_code = parts[1]
                    operator_names = {
                        "310260": "T-Mobile",
                        "310120": "Sprint",
                        "311480": "Verizon",
                        "310410": "AT&T",
                        "310150": "AT&T",
                        "310170": "AT&T",
                        "310030": "AT&T",
                        "311580": "US Cellular",
                    }
                    attrs["carrier_name"] = operator_names.get(operator_code, f"Unknown ({operator_code})")
                
                # Store raw value
                attrs["raw_serving_cell"] = serving_cell
        
        return attrs


class RevealCameraSettingsSensor(RevealSensorBase):
    """Camera settings sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the camera settings sensor."""
        super().__init__(coordinator, camera_id, camera_name, "camera_settings")
        self._attr_name = "Camera Settings"
        self._attr_icon = "mdi:camera-settings"

    @property
    def native_value(self) -> Optional[str]:
        """Return the camera mode."""
        camera_data = self._get_camera_data()
        
        if "settings" in camera_data:
            settings = camera_data["settings"]
            
            # Find camera mode setting
            for setting in settings:
                if setting.get("option") == "Camera Mode":
                    return setting.get("function", "Unknown")
        
        return "Unknown"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes with all camera settings."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "settings" in camera_data:
            settings = camera_data["settings"]
            
            # Parse all settings into readable attributes
            for setting in settings:
                option = setting.get("option")
                function = setting.get("function")
                
                if option and function:
                    # Convert option name to attribute key
                    attr_key = option.lower().replace(" ", "_").replace("-", "_")
                    
                    # Store the setting value
                    attrs[attr_key] = function
                    
                    # Add specific interpretations for key settings
                    if option == "Image Size":
                        attrs["photo_resolution"] = function
                    elif option == "Video Size":
                        attrs["video_resolution"] = function
                    elif option == "Video Length":
                        attrs["video_duration"] = f"{function} seconds"
                    elif option == "Multi Shot":
                        if function != "1P":
                            attrs["burst_mode"] = function
                    elif option == "Night Mode":
                        attrs["night_mode_setting"] = function
                    elif option == "Flash Type":
                        attrs["flash_type"] = function
                    elif option == "Motion Sensitivity":
                        if function.startswith("Level "):
                            attrs["motion_detection_level"] = function
                        elif function == "OFF":
                            attrs["motion_detection_level"] = "Disabled"
                        else:
                            attrs["motion_detection_level"] = function
                    elif option == "GPS Switch":
                        attrs["gps_enabled"] = function == "ON"
                    elif option == "FTP":
                        attrs["ftp_enabled"] = function == "ON"
                    elif option == "SD Loop":
                        attrs["sd_loop_recording"] = function == "ON"
        
        # Add other camera configuration info
        if "activeGps" in camera_data:
            attrs["gps_active"] = camera_data["activeGps"] == "on"
        
        if "location" in camera_data:
            attrs["camera_location"] = camera_data["location"]
        
        if "zip" in camera_data:
            attrs["zip_code"] = camera_data["zip"]
        
        return attrs


class RevealPhotosTakenSensor(RevealSensorBase):
    """Photos taken sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the photos taken sensor."""
        super().__init__(coordinator, camera_id, camera_name, "photos_taken")
        self._attr_name = "Photos Taken"
        self._attr_icon = "mdi:camera-burst"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> Optional[int]:
        """Return the number of photos taken."""
        camera_data = self._get_camera_data()
        
        if "usage" in camera_data:
            photos = camera_data["usage"].get("photos")
            if photos is not None:
                try:
                    return int(photos)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "usage" in camera_data:
            usage = camera_data["usage"]
            if "storedPhotos" in usage:
                stored = usage["storedPhotos"]
                photos = usage.get("photos", 0)
                try:
                    attrs["transmitted_photos"] = int(photos) - int(stored)
                except (ValueError, TypeError):
                    pass
        
        return attrs


class RevealStoredPhotosSensor(RevealSensorBase):
    """Stored photos sensor for Reveal Cell Cam."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, camera_id: str, camera_name: str
    ) -> None:
        """Initialize the stored photos sensor."""
        super().__init__(coordinator, camera_id, camera_name, "stored_photos")
        self._attr_name = "Stored Photos"
        self._attr_icon = "mdi:sd"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the number of stored photos."""
        camera_data = self._get_camera_data()
        
        if "usage" in camera_data:
            stored = camera_data["usage"].get("storedPhotos")
            if stored is not None:
                try:
                    return int(stored)
                except (ValueError, TypeError):
                    pass
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        camera_data = self._get_camera_data()
        
        if "usage" in camera_data:
            usage = camera_data["usage"]
            photos = usage.get("photos", 0)
            stored = usage.get("storedPhotos", 0)
            
            try:
                attrs["total_photos"] = int(photos)
                attrs["pending_transmission"] = int(stored) > 0
            except (ValueError, TypeError):
                pass
        
        return attrs