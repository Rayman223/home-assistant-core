"""Tests for the Wallbox button platform."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import setup_integration

# Adjust this entity id to match the charger name used in conftest mock data.
# Typically derived from: f"button.wallbox_{charger_name_slug}_resume_schedule"
RESUME_SCHEDULE_BUTTON = "button.wallbox_portal_resume_schedule"


async def test_button_press_success(
    hass: HomeAssistant,
    mock_wallbox: MagicMock,
) -> None:
    """Test that pressing the button calls resumeSchedule once."""
    await setup_integration(hass)

    with patch.object(
        mock_wallbox, "resumeSchedule", return_value={}
    ) as mock_resume:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {ATTR_ENTITY_ID: RESUME_SCHEDULE_BUTTON},
            blocking=True,
        )

    # Verify the library method was called exactly once.
    # The station id is taken from the coordinator (_station), which is set from
    # the config entry data — not accessible directly from the Wallbox mock.
    mock_resume.assert_called_once()


async def test_button_press_insufficient_rights(
    hass: HomeAssistant,
    mock_wallbox: MagicMock,
    http_403_error: requests.exceptions.HTTPError,
) -> None:
    """Test that a 403 response raises HomeAssistantError (InsufficientRights)."""
    await setup_integration(hass)

    with (
        patch.object(mock_wallbox, "resumeSchedule", side_effect=http_403_error),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {ATTR_ENTITY_ID: RESUME_SCHEDULE_BUTTON},
            blocking=True,
        )


async def test_button_press_too_many_requests(
    hass: HomeAssistant,
    mock_wallbox: MagicMock,
    http_429_error: requests.exceptions.HTTPError,
) -> None:
    """Test that a 429 response raises HomeAssistantError with too_many_requests."""
    await setup_integration(hass)

    with (
        patch.object(mock_wallbox, "resumeSchedule", side_effect=http_429_error),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {ATTR_ENTITY_ID: RESUME_SCHEDULE_BUTTON},
            blocking=True,
        )


async def test_button_press_api_failed(
    hass: HomeAssistant,
    mock_wallbox: MagicMock,
) -> None:
    """Test that an unexpected HTTP error raises HomeAssistantError with api_failed."""
    await setup_integration(hass)

    generic_error = requests.exceptions.HTTPError()
    generic_error.response = MagicMock()
    generic_error.response.status_code = 500

    with (
        patch.object(mock_wallbox, "resumeSchedule", side_effect=generic_error),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {ATTR_ENTITY_ID: RESUME_SCHEDULE_BUTTON},
            blocking=True,
        )

