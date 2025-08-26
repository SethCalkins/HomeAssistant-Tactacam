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

    async def close(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None