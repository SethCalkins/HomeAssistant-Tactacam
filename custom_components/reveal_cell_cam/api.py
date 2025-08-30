"""API client for Reveal Cell Cam."""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from .const import API_BASE_URL, API_VERSION, USER_AGENT

_LOGGER = logging.getLogger(__name__)

COGNITO_URL = "https://cognito-idp.us-east-1.amazonaws.com/"
COGNITO_CLIENT_ID = "6r9tpojvgvkci5trla0ip14mon"


class RevealCellCamAPI:
    """API client for Reveal Cell Cam service."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._id_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._account_id: Optional[str] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def authenticate(self) -> bool:
        """Authenticate with AWS Cognito to get tokens."""
        session = await self._ensure_session()
        
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "X-Amz-User-Agent": "aws-amplify/6.8.2 auth/4 framework/1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Origin": "https://account.revealcellcam.com",
            "Referer": "https://account.revealcellcam.com/",
        }
        
        data = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "AuthParameters": {
                "USERNAME": self.username,
                "PASSWORD": self.password
            },
            "ClientId": COGNITO_CLIENT_ID
        }
        
        try:
            async with session.post(COGNITO_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    # Read as text first to avoid content-type issues
                    text = await response.text()
                    auth_result = json.loads(text)
                    if "AuthenticationResult" in auth_result:
                        auth_data = auth_result["AuthenticationResult"]
                        self._access_token = auth_data.get("AccessToken")
                        self._id_token = auth_data.get("IdToken")
                        self._refresh_token = auth_data.get("RefreshToken")
                        
                        # Calculate token expiry
                        expires_in = auth_data.get("ExpiresIn", 43200)  # Default 12 hours
                        self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
                        
                        _LOGGER.info("Successfully authenticated with Cognito")
                        
                        # Get account info
                        await self._get_account_info()
                        return True
                    
                _LOGGER.error("Authentication failed: %s", response.status)
                return False
                
        except aiohttp.ClientError as err:
            _LOGGER.error("Error during authentication: %s", err)
            return False

    async def _ensure_authenticated(self) -> bool:
        """Ensure we have valid authentication tokens."""
        if not self._access_token or not self._token_expiry:
            return await self.authenticate()
        
        # Check if token is about to expire (5 minutes buffer)
        if datetime.now() >= self._token_expiry - timedelta(minutes=5):
            if self._refresh_token:
                return await self._refresh_tokens()
            else:
                return await self.authenticate()
        
        return True

    async def _refresh_tokens(self) -> bool:
        """Refresh authentication tokens using refresh token."""
        if not self._refresh_token:
            return await self.authenticate()
        
        session = await self._ensure_session()
        
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "X-Amz-User-Agent": "aws-amplify/6.8.2 auth/4 framework/1",
        }
        
        data = {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "AuthParameters": {
                "REFRESH_TOKEN": self._refresh_token
            },
            "ClientId": COGNITO_CLIENT_ID
        }
        
        try:
            async with session.post(COGNITO_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    # Read as text first to avoid content-type issues
                    text = await response.text()
                    auth_result = json.loads(text)
                    if "AuthenticationResult" in auth_result:
                        auth_data = auth_result["AuthenticationResult"]
                        self._access_token = auth_data.get("AccessToken")
                        self._id_token = auth_data.get("IdToken")
                        
                        expires_in = auth_data.get("ExpiresIn", 43200)
                        self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
                        
                        _LOGGER.info("Successfully refreshed tokens")
                        return True
                    
                _LOGGER.error("Token refresh failed: %s", response.status)
                return False
                
        except aiohttp.ClientError as err:
            _LOGGER.error("Error during token refresh: %s", err)
            return False

    async def _get_account_info(self) -> None:
        """Get account information."""
        session = await self._ensure_session()
        url = f"{API_BASE_URL}/{API_VERSION}/account"
        
        # Headers already include the Access Token if authenticated
        headers = self._get_headers()
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if "response" in data:
                        account_data = data["response"].get("account", data.get("response"))
                        if account_data:
                            self._account_id = account_data.get("accountId")
                            _LOGGER.info("Retrieved account ID: %s", self._account_id)
                elif response.status == 401:
                    _LOGGER.warning("Unauthorized access to account info, might work without auth")
                else:
                    _LOGGER.warning("Failed to get account info: %s", response.status)
                        
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching account info: %s", err)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for API requests."""
        headers = {
            "reveal-user-agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://account.revealcellcam.com",
            "Referer": "https://account.revealcellcam.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        
        # Use Access Token for Authorization (not ID Token)
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        
        return headers

    async def get_cameras(self) -> List[Dict[str, Any]]:
        """Get list of cameras."""
        await self._ensure_authenticated()
        
        session = await self._ensure_session()
        url = f"{API_BASE_URL}/{API_VERSION}/cameras"
        
        headers = self._get_headers()
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    cameras = data.get("response", {}).get("cameras", [])
                    _LOGGER.info("Found %d cameras", len(cameras))
                    return cameras
                else:
                    _LOGGER.error("Failed to get cameras: HTTP %s", response.status)
                    text = await response.text()
                    _LOGGER.debug("Response: %s", text[:500])
                    return []
                
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching cameras: %s", err)
            return []

    async def get_photos(self, size: int = 100, page: int = 0, camera_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get photos from cameras."""
        await self._ensure_authenticated()
        
        session = await self._ensure_session()
        url = f"{API_BASE_URL}/{API_VERSION}/photos"
        
        params = {
            "size": size,
            "page": page,
            "includeWeatherData": "true"
        }
        
        if camera_id:
            params["cameraId"] = camera_id
        
        headers = self._get_headers()
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    photos = data.get("response", {}).get("photos", [])
                    _LOGGER.debug("Retrieved %d photos for camera %s", len(photos), camera_id or "all")
                    
                    # Log first photo details for debugging
                    if photos and len(photos) > 0:
                        first_photo = photos[0]
                        _LOGGER.debug("First photo has weatherData: %s, metadata: %s", 
                                    "weatherData" in first_photo,
                                    "metadata" in first_photo)
                    
                    return photos
                else:
                    _LOGGER.error("Failed to get photos: HTTP %s", response.status)
                    text = await response.text()
                    _LOGGER.debug("Response: %s", text[:500])
                    return []
                
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching photos: %s", err)
            return []

    async def get_camera_stats(self, camera_id: str) -> Dict[str, Any]:
        """Get statistics for a specific camera."""
        if not await self._ensure_authenticated():
            return {}
        
        session = await self._ensure_session()
        url = f"{API_BASE_URL}/{API_VERSION}/cameras/{camera_id}/stats"
        
        headers = {
            "Authorization": f"Bearer {self._id_token}",
            "reveal-user-agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://account.revealcellcam.com",
            "Referer": "https://account.revealcellcam.com/",
        }
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response", {})
                elif response.status == 404:
                    # Stats endpoint might not exist, try alternative
                    return await self._calculate_camera_stats(camera_id)
                    
                _LOGGER.error("Failed to get camera stats: %s", response.status)
                return {}
                
        except aiohttp.ClientError as err:
            _LOGGER.debug("Error fetching camera stats, will calculate locally: %s", err)
            return await self._calculate_camera_stats(camera_id)

    async def _calculate_camera_stats(self, camera_id: str) -> Dict[str, Any]:
        """Calculate camera statistics from photos."""
        photos = await self.get_photos(size=1000, camera_id=camera_id)
        
        if not photos:
            return {}
        
        stats = {
            "total_photos": len(photos),
            "last_photo_date": photos[0].get("photoDateUtc") if photos else None,
            "first_photo_date": photos[-1].get("photoDateUtc") if photos else None,
        }
        
        # Calculate battery stats
        battery_levels = [int(p.get("metadata", {}).get("batteryLevel", 0)) for p in photos[:10] if p.get("metadata", {}).get("batteryLevel")]
        if battery_levels:
            stats["average_battery"] = sum(battery_levels) / len(battery_levels)
            stats["current_battery"] = battery_levels[0]
        
        # Calculate signal stats
        signal_levels = [int(p.get("metadata", {}).get("signal", 0)) for p in photos[:10] if p.get("metadata", {}).get("signal")]
        if signal_levels:
            stats["average_signal"] = sum(signal_levels) / len(signal_levels)
            stats["current_signal"] = signal_levels[0]
        
        return stats

    async def get_latest_photo_for_camera(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest photo for a specific camera."""
        photos = await self.get_photos(size=1, camera_id=camera_id)
        return photos[0] if photos else None

    async def async_get_data(self) -> Dict[str, Any]:
        """Fetch all data from API."""
        cameras = await self.get_cameras()
        
        if not cameras:
            _LOGGER.warning("No cameras found")
            return {"cameras": [], "photos": []}
        
        # Get latest photo for each camera individually to ensure weather data
        for camera in cameras:
            camera_id = camera.get("cameraId")
            if camera_id:
                # Get latest photo with weather data for this specific camera
                latest_photo = await self.get_latest_photo_for_camera(camera_id)
                if latest_photo:
                    camera["latest_photo"] = latest_photo
                    _LOGGER.debug("Camera %s has latest photo with weather data: %s", 
                                camera_id, 
                                "weatherData" in latest_photo)
                else:
                    _LOGGER.warning("No photos found for camera %s", camera_id)
                
                # Add stats
                stats = await self._calculate_camera_stats(camera_id)
                camera["stats"] = stats
        
        # Also get a batch of recent photos for history
        all_photos = await self.get_photos(size=20)
        
        return {
            "cameras": cameras,
            "photos": all_photos  # Keep last 20 photos for history
        }

    async def update_camera_settings(self, camera_id: str, settings: List[Dict[str, Any]]) -> bool:
        """Update camera settings.
        
        Args:
            camera_id: The camera ID to update
            settings: List of settings to update
            
        Returns:
            True if successful, False otherwise
        """
        if not await self._ensure_authenticated():
            return False
        
        session = await self._ensure_session()
        url = f"{API_BASE_URL}/{API_VERSION}/cameras/{camera_id}"
        
        headers = self._get_headers()
        
        # Prepare the payload
        payload = {
            "settings": settings
        }
        
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully updated settings for camera %s", camera_id)
                    return True
                else:
                    _LOGGER.error("Failed to update camera settings: HTTP %s", response.status)
                    text = await response.text()
                    _LOGGER.debug("Response: %s", text[:500])
                    return False
                    
        except aiohttp.ClientError as err:
            _LOGGER.error("Error updating camera settings: %s", err)
            return False

    async def set_motion_sensitivity(self, camera_id: str, level: int) -> bool:
        """Set motion sensitivity for a camera.
        
        Args:
            camera_id: The camera ID
            level: Sensitivity level (0 = OFF, 1-9 = levels)
            
        Returns:
            True if successful
        """
        # Get current camera settings first
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            _LOGGER.error("Camera %s not found or has no settings", camera_id)
            return False
        
        # Copy all current settings
        settings = camera["settings"].copy()
        
        # Update motion sensitivity
        for setting in settings:
            if setting.get("option") == "Motion Sensitivity":
                setting["code"] = f"{level}#"
                if level == 0:
                    setting["function"] = "OFF"
                else:
                    setting["function"] = f"Level {level}" if level > 0 else str(level)
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def set_camera_mode(self, camera_id: str, mode: str) -> bool:
        """Set camera mode.
        
        Args:
            camera_id: The camera ID
            mode: "photo" or "photo_video"
            
        Returns:
            True if successful
        """
        # Get current camera settings
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            return False
        
        settings = camera["settings"].copy()
        
        for setting in settings:
            if setting.get("option") == "Camera Mode":
                if mode == "photo":
                    setting["code"] = "$R01*1#"
                    setting["function"] = "Photo（Default)"
                else:
                    setting["code"] = "$R01*2#"
                    setting["function"] = "PIC+Video"
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def set_video_length(self, camera_id: str, length: int) -> bool:
        """Set video recording length.
        
        Args:
            camera_id: The camera ID
            length: Video length in seconds (10, 15, 30, etc.)
            
        Returns:
            True if successful
        """
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            return False
        
        settings = camera["settings"].copy()
        
        for setting in settings:
            if setting.get("option") == "Video Length":
                setting["code"] = f"$V07*{length}#"
                setting["function"] = f"{length}S"
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def request_photo(self, camera_id: str) -> bool:
        """Request an on-demand photo from camera.
        
        Args:
            camera_id: The camera ID
            
        Returns:
            True if successful
        """
        if not await self._ensure_authenticated():
            return False
        
        session = await self._ensure_session()
        url = f"{API_BASE_URL}/{API_VERSION}/cameras/{camera_id}/photo-request"
        
        headers = self._get_headers()
        
        try:
            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully requested photo from camera %s", camera_id)
                    return True
                else:
                    _LOGGER.error("Failed to request photo: HTTP %s", response.status)
                    return False
                    
        except aiohttp.ClientError as err:
            _LOGGER.error("Error requesting photo: %s", err)
            return False

    async def request_video(self, camera_id: str) -> bool:
        """Request an on-demand video from camera.
        
        Args:
            camera_id: The camera ID
            
        Returns:
            True if successful
        """
        if not await self._ensure_authenticated():
            return False
        
        session = await self._ensure_session()
        url = f"{API_BASE_URL}/{API_VERSION}/cameras/{camera_id}/video-request"
        
        headers = self._get_headers()
        
        try:
            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully requested video from camera %s", camera_id)
                    return True
                else:
                    _LOGGER.error("Failed to request video: HTTP %s", response.status)
                    return False
                    
        except aiohttp.ClientError as err:
            _LOGGER.error("Error requesting video: %s", err)
            return False

    async def set_night_mode(self, camera_id: str, mode: str) -> bool:
        """Set night mode for a camera.
        
        Args:
            camera_id: The camera ID
            mode: "max_range", "balance", or "min_blur"
            
        Returns:
            True if successful
        """
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            return False
        
        settings = camera["settings"].copy()
        
        mode_map = {
            "max_range": ("$NM00*1#", "Max Range"),
            "balance": ("$NM00*2#", "Balance"),
            "min_blur": ("$NM00*3#", "Min Blur")
        }
        
        if mode not in mode_map:
            return False
        
        code, function = mode_map[mode]
        
        for setting in settings:
            if setting.get("option") == "Night Mode":
                setting["code"] = code
                setting["function"] = function
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def set_flash_type(self, camera_id: str, flash_type: str) -> bool:
        """Set flash type for a camera.
        
        Args:
            camera_id: The camera ID
            flash_type: "low_glow" or "no_glow"
            
        Returns:
            True if successful
        """
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            return False
        
        settings = camera["settings"].copy()
        
        flash_map = {
            "low_glow": ("$FT01*1#", "Low Glow"),
            "no_glow": ("$FT01*0#", "No Glow")
        }
        
        if flash_type not in flash_map:
            return False
        
        code, function = flash_map[flash_type]
        
        for setting in settings:
            if setting.get("option") == "Flash Type":
                setting["code"] = code
                setting["function"] = function
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def set_multi_shot(self, camera_id: str, count: int, interval: int) -> bool:
        """Set multi-shot (burst mode) settings.
        
        Args:
            camera_id: The camera ID
            count: Number of photos (1-9)
            interval: Seconds between shots
            
        Returns:
            True if successful
        """
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            return False
        
        settings = camera["settings"].copy()
        
        # Build the function string
        if count == 1:
            function = "1P"
            code = "$N09*01+0#"
        else:
            function = f"{count}P/{interval}s"
            code = f"$N09*{count:02d}+{interval}#"
        
        for setting in settings:
            if setting.get("option") == "Multi Shot":
                setting["code"] = code
                setting["function"] = function
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def set_image_resolution(self, camera_id: str, resolution: str) -> bool:
        """Set image resolution.
        
        Args:
            camera_id: The camera ID
            resolution: "4k" or "2.5k"
            
        Returns:
            True if successful
        """
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            return False
        
        settings = camera["settings"].copy()
        
        res_map = {
            "4k": ("$S00*32#", "32M(UHD 4K)"),
            "2.5k": ("$S00*20#", "20M(WQHD 2.5K)")
        }
        
        if resolution not in res_map:
            return False
        
        code, function = res_map[resolution]
        
        for setting in settings:
            if setting.get("option") == "Image Size":
                setting["code"] = code
                setting["function"] = function
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def set_video_resolution(self, camera_id: str, resolution: str) -> bool:
        """Set video resolution.
        
        Args:
            camera_id: The camera ID
            resolution: "1080p", "720p", or "wvga"
            
        Returns:
            True if successful
        """
        cameras = await self.get_cameras()
        camera = None
        for cam in cameras:
            if cam.get("cameraId") == camera_id:
                camera = cam
                break
        
        if not camera or "settings" not in camera:
            return False
        
        settings = camera["settings"].copy()
        
        res_map = {
            "1080p": ("$V06*2#", "FHD 1080P"),
            "720p": ("$V06*1#", "HD 720P"),
            "wvga": ("$V06*0#", "WVGA")
        }
        
        if resolution not in res_map:
            return False
        
        code, function = res_map[resolution]
        
        for setting in settings:
            if setting.get("option") == "Video Size":
                setting["code"] = code
                setting["function"] = function
                break
        
        return await self.update_camera_settings(camera_id, settings)

    async def close(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None