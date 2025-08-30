# Troubleshooting Camera Display Issues

## Camera Entity Not Showing in Dashboard

### 1. Check if Camera Entities Exist

Go to **Developer Tools → States** in Home Assistant and search for:
- `camera.ao_cam01`
- `camera.ao_cam02`

**If entities don't exist:**
- Restart Home Assistant
- Check Configuration → Integrations → Reveal Cell Cam
- Check logs for errors

**If entities exist but show as "unavailable":**
- The camera might not have any photos
- Check if the API is returning data
- Look at entity attributes for clues

### 2. Check Entity Names

The actual entity IDs might be different than expected. Common variations:
- `camera.ao_cam01` vs `camera.reveal_ao_cam01`
- `camera.ao_cam01` vs `camera.ao_cam01_2` (if duplicates)
- `camera.ao_cam01` vs `camera.camera_xxxx` (using camera ID)

**To find the correct entity ID:**
1. Go to Developer Tools → States
2. Filter by "camera."
3. Look for entities with "reveal" in attributes

### 3. Dashboard Configuration Issues

#### Manual Dashboard Configuration
If using YAML mode, ensure your dashboard includes the camera entities:

```yaml
- type: picture-entity
  entity: camera.ao_cam02  # Make sure this matches the actual entity ID
  camera_view: auto
```

#### UI Dashboard Configuration
1. Edit your dashboard
2. Add a new card
3. Choose "Picture Entity" or "Picture Glance"
4. Select the camera entity from the dropdown
5. If the entity doesn't appear in dropdown, it doesn't exist

### 4. Common Issues and Solutions

#### Issue: Camera shows "No Image"
**Solutions:**
- Camera might not have taken any photos yet
- Check if `photoUrl` exists in entity attributes
- Try manually refreshing the integration

#### Issue: Camera entity exists but not in dashboard
**Solutions:**
- Entity ID in dashboard doesn't match actual entity ID
- Dashboard card type doesn't support camera entities
- Browser cache issue - try Ctrl+F5 to hard refresh

#### Issue: One camera works, another doesn't
**Possible causes:**
- Different data structure from API for each camera
- One camera has no photos
- Entity naming inconsistency

**To diagnose:**
1. Compare entity attributes of both cameras
2. Look for differences in:
   - `last_photo_time`
   - `photoUrl` in attributes
   - Device info

### 5. Check Entity Attributes

In Developer Tools → States, click on the camera entity and check attributes:

**Working camera should have:**
```yaml
friendly_name: AO-CAM01
supported_features: 1
entity_picture: /api/camera_proxy/camera.ao_cam01?...
access_token: ...
```

**Non-working camera might show:**
```yaml
friendly_name: AO-CAM02
supported_features: 1
# Missing entity_picture or showing placeholder
```

### 6. Force Refresh

Try these steps in order:
1. Go to Configuration → Integrations → Reveal Cell Cam
2. Click the 3 dots → Reload
3. Wait 30 seconds
4. Check if camera appears
5. If not, restart Home Assistant

### 7. Check Logs

Look for specific error messages:
```
# Check for camera setup errors
grep "AO-CAM02" home-assistant.log

# Check for image fetch errors
grep "Failed to fetch image" home-assistant.log

# Check for API errors
grep "photoUrl" home-assistant.log
```

### 8. Entity Registry Issues

Sometimes entities get stuck in the registry:
1. Go to Configuration → Integrations → Reveal Cell Cam
2. Click on devices/entities
3. Look for duplicate or disabled entities
4. Enable any disabled camera entities
5. Remove duplicates if present

### 9. Quick Fix - Add Camera Manually

If the entity exists but won't show in UI editor:
1. Edit dashboard in YAML mode
2. Add this card:

```yaml
type: picture-entity
entity: camera.ao_cam02  # Use actual entity ID from States
camera_view: auto
name: AO-CAM02
```

### 10. Test with Simple Card

Create a test card to isolate the issue:

```yaml
type: markdown
content: |
  ## Camera Test
  AO-CAM01 State: {{ states('camera.ao_cam01') }}
  AO-CAM02 State: {{ states('camera.ao_cam02') }}
  
  AO-CAM01 Exists: {{ states('camera.ao_cam01') != 'unknown' }}
  AO-CAM02 Exists: {{ states('camera.ao_cam02') != 'unknown' }}
```

This will show if the entities exist and their current states.