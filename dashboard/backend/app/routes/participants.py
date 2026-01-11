"""
Participant Routes

Endpoints for participant registration and avatar upload.
"""

import secrets
import random
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..config import MAP_WIDTH, MAP_HEIGHT
from ..database import (
    get_event,
    get_participant,
    create_participant,
    update_participant,
    check_username_exists,
)
from ..storage import upload_avatar_image, get_avatar_url
from ..models import (
    ParticipantInit,
    ParticipantInitResponse,
    ParticipantRegister,
    ParticipantResponse,
    ParticipantUpdate,
)


router = APIRouter(prefix="/participants", tags=["Participants"])


@router.get("/{participant_id}", response_model=ParticipantResponse)
async def get_participant_info(participant_id: str):
    """
    Get participant information by ID.

    Used by agents to fetch evidence URLs and other participant context.
    """
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return ParticipantResponse(**participant)


@router.post("/init", response_model=ParticipantInitResponse)
async def init_participant(data: ParticipantInit):
    """
    Initialize a new participant (reserve username and assign coordinates).

    Used by setup.sh after username validation.
    """
    # Verify event exists and is active
    event = await get_event(data.event_code)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not event.get("active", True):
        raise HTTPException(status_code=410, detail="Event has ended")

    # Check participant limit
    if event.get("participant_count", 0) >= event.get("max_participants", 500):
        raise HTTPException(status_code=409, detail="Event is full")

    # Double-check username availability (race condition protection)
    if await check_username_exists(data.event_code, data.username):
        raise HTTPException(status_code=409, detail="Username already taken")

    # Generate unique participant ID and random starting coordinates
    participant_id = secrets.token_hex(4)  # 8 character hex string
    starting_x = random.randint(10, MAP_WIDTH - 10)
    starting_y = random.randint(10, MAP_HEIGHT - 10)

    # Create participant record
    participant = {
        "participant_id": participant_id,
        "username": data.username,
        "event_code": data.event_code,
        "project_id": data.project_id,
        "x": starting_x,
        "y": starting_y,
        "location_confirmed": False,
        "portrait_url": None,
        "icon_url": None,
        "suit_color": None,
        "appearance": None,
        "registered_at": None,
        "created_at": datetime.now(timezone.utc),
        "active": True,
    }

    await create_participant(participant)

    return ParticipantInitResponse(
        participant_id=participant_id,
        username=data.username,
        event_code=data.event_code,
        starting_x=starting_x,
        starting_y=starting_y,
    )


@router.post("/{participant_id}/avatar")
async def upload_avatar(
    participant_id: str,
    portrait: UploadFile = File(...),
    icon: UploadFile = File(...),
):
    """
    Upload avatar images (portrait and icon) for a participant.

    Used by create_identity.py after image generation.
    """
    # Verify participant exists
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Validate file types
    for file, name in [(portrait, "portrait"), (icon, "icon")]:
        if file.content_type not in ["image/png", "image/jpeg"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {name} file type. Must be PNG or JPEG."
            )

    # Upload images to Firebase Storage
    event_code = participant["event_code"]

    portrait_bytes = await portrait.read()
    portrait_path = f"avatars/{event_code}/{participant_id}/portrait.png"
    await upload_avatar_image(portrait_path, portrait_bytes, portrait.content_type)
    portrait_url = get_avatar_url(portrait_path)

    icon_bytes = await icon.read()
    icon_path = f"avatars/{event_code}/{participant_id}/icon.png"
    await upload_avatar_image(icon_path, icon_bytes, icon.content_type)
    icon_url = get_avatar_url(icon_path)

    # Update participant record with avatar URLs
    await update_participant(participant_id, {
        "portrait_url": portrait_url,
        "icon_url": icon_url,
    })

    return {
        "status": "success",
        "portrait_url": portrait_url,
        "icon_url": icon_url,
    }


@router.post("/register", response_model=ParticipantResponse)
async def register_participant(data: ParticipantRegister):
    """
    Complete participant registration.

    Used by create_identity.py after avatar upload.
    """
    # Verify participant exists
    participant = await get_participant(data.participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Check if avatar has been uploaded
    if not participant.get("portrait_url") or not participant.get("icon_url"):
        raise HTTPException(
            status_code=400,
            detail="Avatar must be uploaded before registration"
        )

    # Update participant with registration info
    updates = {
        "registered_at": datetime.now(timezone.utc),
        "active": True,
    }

    if data.suit_color:
        updates["suit_color"] = data.suit_color
    if data.appearance:
        updates["appearance"] = data.appearance

    await update_participant(data.participant_id, updates)

    # Return updated participant
    updated = await get_participant(data.participant_id)
    return ParticipantResponse(**updated)


@router.post("/{participant_id}/evidence")
async def upload_evidence(
        participant_id: str,
        soil_sample: UploadFile = File(...),
        star_field: UploadFile = File(...),
        flora_recording: UploadFile = File(...),
):
    """
    Upload crash site evidence (soil, flora, stars) for a participant.

    Used by Level 1 generate_evidence.py after evidence generation.
    """
    # Verify participant exists
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    event_code = participant["event_code"]
    urls = {}

    # Upload each evidence file
    evidence_files = [
        (soil_sample, "soil_sample", "soil"),
        (star_field, "star_field", "stars"),
        (flora_recording, "flora_recording", "flora"),
    ]

    for file, filename, url_key in evidence_files:
        file_bytes = await file.read()

        # Determine extension from content type
        if "video" in file.content_type:
            ext = "mp4"
        elif "png" in file.content_type:
            ext = "png"
        else:
            ext = "jpg"

        path = f"evidence/{event_code}/{participant_id}/{filename}.{ext}"
        await upload_avatar_image(path, file_bytes, file.content_type)
        urls[url_key] = get_avatar_url(path)

    # Update participant record with evidence URLs
    await update_participant(participant_id, {
        "evidence_urls": urls,
    })

    return {
        "status": "success",
        "evidence_urls": urls,
    }


@router.patch("/{participant_id}/location")
async def confirm_location(participant_id: str, x: int, y: int):
    """
    Confirm participant's exact location (used in Level 1).

    Updates location_confirmed to True and sets precise coordinates.
    """
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    await update_participant(participant_id, {
        "x": x,
        "y": y,
        "location_confirmed": True,
    })

    return {"status": "success", "x": x, "y": y, "location_confirmed": True}


@router.patch("/{participant_id}", response_model=ParticipantResponse)
async def update_participant_details(participant_id: str, updates: ParticipantUpdate):
    """
    Update participant details (including level overrides).

    Used by developers or admin tools to manually set progress.
    """
    # Verify participant exists
    participant = await get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Filter out None values to only update provided fields
    update_data = {k: v for k, v in updates.dict().items() if v is not None}

    if not update_data:
        return ParticipantResponse(**participant)

    await update_participant(participant_id, update_data)

    # Return updated participant
    updated = await get_participant(participant_id)
    return ParticipantResponse(**updated)
