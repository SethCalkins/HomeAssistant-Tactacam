"""Camera platform for Reveal Cell Cam."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reveal Cell Cam camera based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    cameras = []
    for camera_data in coordinator.data.get("cameras", []):
        camera_id = camera_data.get("cameraId", "unknown")
        camera_name = camera_data.get("cameraName") or camera_data.get("cameraLocation") or camera_data.get("name") or f"Camera {camera_id[-4:]}"
        _LOGGER.info("Setting up camera entity: %s (ID: %s)", camera_name, camera_id)
        
        # Log if latest_photo exists
        if "latest_photo" in camera_data:
            has_url = "photoUrl" in camera_data["latest_photo"]
            _LOGGER.info("Camera %s has latest_photo with photoUrl: %s", camera_name, has_url)
        else:
            _LOGGER.warning("Camera %s has no latest_photo data", camera_name)
            
        cameras.append(RevealCellCamCamera(coordinator, camera_data, api))

    _LOGGER.info("Created %d camera entities", len(cameras))
    async_add_entities(cameras, update_before_add=True)


class RevealCellCamCamera(CoordinatorEntity, Camera):
    """Representation of a Reveal Cell Cam camera."""

    def __init__(
        self, 
        coordinator: DataUpdateCoordinator, 
        camera_data: Dict[str, Any],
        api: Any
    ) -> None:
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        
        self._camera_data = camera_data
        self._api = api
        self._camera_id = camera_data.get("cameraId", "")
        # Try multiple fields for camera name, matching sensor.py logic
        self._camera_name = camera_data.get("cameraName") or camera_data.get("cameraLocation") or camera_data.get("name") or f"Camera {self._camera_id[-4:]}"
        self._attr_name = self._camera_name
        self._attr_unique_id = f"reveal_cell_cam_{self._camera_id}"
        
        # Enable stream support if available
        self._attr_supported_features = CameraEntityFeature(0)
        
        # Device info with more details
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._camera_id)},
            name=self._camera_name,  # Use camera name directly for device
            manufacturer="Tactacam",
            model=camera_data.get("cameraModel", "Reveal Cell Cam"),
            sw_version=camera_data.get("firmwareVersion"),
            hw_version=camera_data.get("hardwareVersion"),
        )
        
        _LOGGER.debug("Initialized camera entity: %s with unique_id: %s", self._attr_name, self._attr_unique_id)
        
        self._image_url: Optional[str] = None
        self._image: Optional[bytes] = None
        self._last_image_fetch: Optional[datetime] = None

    def _get_camera_data(self) -> Dict[str, Any]:
        """Get the current camera data from coordinator."""
        for camera in self.coordinator.data.get("cameras", []):
            if camera.get("cameraId") == self._camera_id:
                return camera
        return self._camera_data

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        camera_data = self._get_camera_data()
        
        attrs = {
            "camera_id": self._camera_id,
            "camera_name": self._camera_name,
            "location": camera_data.get("cameraLocation"),
            "status": camera_data.get("status", "active"),
            "firmware_version": camera_data.get("firmwareVersion"),
            "hardware_version": camera_data.get("hardwareVersion"),
        }
        
        # Add camera stats
        stats = camera_data.get("stats", {})
        if stats:
            attrs.update({
                "total_photos": stats.get("total_photos", 0),
                "first_photo_date": stats.get("first_photo_date"),
                "average_battery": round(stats.get("average_battery", 0), 1) if stats.get("average_battery") else None,
                "average_signal": round(stats.get("average_signal", 0), 1) if stats.get("average_signal") else None,
            })
        
        # Add latest photo details
        latest_photo = camera_data.get("latest_photo")
        if latest_photo:
            attrs.update({
                "last_photo_time": latest_photo.get("photoDateUtc"),
                "last_photo_filename": latest_photo.get("filename"),
                "battery_level": latest_photo.get("metadata", {}).get("batteryLevel"),
                "signal_strength": latest_photo.get("metadata", {}).get("signal"),
                "hd_photo": latest_photo.get("hdPhoto", False),
            })
            
            # Weather data
            weather = latest_photo.get("weatherRecord", {})
            if weather:
                attrs.update({
                    "temperature": weather.get("temperature"),
                    "weather": weather.get("weatherLabel"),
                    "moon_phase": weather.get("moonPhase"),
                    "sun_phase": weather.get("sunPhase"),
                    "wind_speed": weather.get("windDirection", {}).get("speed"),
                    "wind_direction": weather.get("windDirection", {}).get("cardinalLabel"),
                    "wind_gust": weather.get("windGust"),
                    "barometric_pressure": weather.get("barometricPressure"),
                    "pressure_tendency": weather.get("pressureTendency"),
                    "temperature_range_12h_min": weather.get("temperatureRange12Hours", {}).get("min"),
                    "temperature_range_12h_max": weather.get("temperatureRange12Hours", {}).get("max"),
                    "temperature_departure_24h": weather.get("past24HoursTemperatureDeparture"),
                })
            
            # GPS location if available
            gps = latest_photo.get("gpsLocation")
            if gps:
                attrs["gps_latitude"] = gps.get("lat")
                attrs["gps_longitude"] = gps.get("lon")
                attrs["gps_coordinates"] = f"{gps.get('lat')}, {gps.get('lon')}"
        
        # Subscription/plan info if available
        if camera_data.get("subscription"):
            attrs["subscription_plan"] = camera_data.get("subscription", {}).get("plan")
            attrs["subscription_status"] = camera_data.get("subscription", {}).get("status")
        
        return attrs

    async def async_camera_image(
        self, width: Optional[int] = None, height: Optional[int] = None
    ) -> Optional[bytes]:
        """Return bytes of camera image."""
        camera_data = self._get_camera_data()
        latest_photo = camera_data.get("latest_photo")
        
        if not latest_photo or "photoUrl" not in latest_photo:
            _LOGGER.debug("No photo URL available for camera %s", self._camera_id)
            return self._image  # Return cached image if available
        
        photo_url = latest_photo["photoUrl"]
        
        # Check if we need to fetch a new image
        if self._image_url != photo_url or not self._image:
            # Fetch the image from the S3 URL
            import aiohttp
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.get(photo_url) as response:
                        if response.status == 200:
                            self._image = await response.read()
                            self._image_url = photo_url
                            self._last_image_fetch = datetime.now()
                            _LOGGER.debug("Successfully fetched image for camera %s", self._camera_id)
                        else:
                            _LOGGER.warning("Failed to fetch image for camera %s: HTTP %s", self._camera_id, response.status)
                except aiohttp.ClientError as err:
                    _LOGGER.error("Error fetching camera image for %s: %s", self._camera_id, err)
                except Exception as err:
                    _LOGGER.error("Unexpected error fetching image for camera %s: %s", self._camera_id, err)
        
        return self._image

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._get_camera_data() is not None

    @property
    def state(self) -> str:
        """Return the state of the camera."""
        camera_data = self._get_camera_data()
        if camera_data and camera_data.get("latest_photo"):
            return "idle"
        return "unknown"

    async def async_update(self) -> None:
        """Update the camera entity."""
        await self.coordinator.async_request_refresh()

    @property
    def brand(self) -> Optional[str]:
        """Return the brand of the camera."""
        return "Tactacam Reveal"

    @property
    def motion_detection_enabled(self) -> bool:
        """Return whether motion detection is enabled."""
        return True  # Trail cameras are motion-activated

    @property
    def is_recording(self) -> bool:
        """Return whether the camera is recording."""
        return False  # Trail cameras take photos, not continuous recording