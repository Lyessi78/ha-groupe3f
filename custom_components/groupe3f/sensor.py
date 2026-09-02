"""Sensor platform for Groupe 3F."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfVolume
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_CONTRACT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    contract_id = entry.data[CONF_CONTRACT_ID]

    entities = []
    # Map JSON boolean keys to (Name, slug used in the external statistic id)
    types = {
        "compteurChaud": ("Eau Chaude", "eau_chaude"),
        "compteurFroid": ("Eau Froide", "eau_froide"),
    }

    for key, (name, slug) in types.items():
        # Check if any data exists for this meter type
        if any(item.get(key) is True for item in coordinator.data):
            entities.append(Groupe3FSensor(hass, coordinator, contract_id, key, name, slug))

    async_add_entities(entities)

class Groupe3FSensor(CoordinatorEntity, SensorEntity):
    """Groupe 3F Sensor.

    The entity only exposes the latest meter index for display. Consumption
    history is published as an external statistic (see _import_historical_statistics),
    so no state_class is set here: that would make the recorder compile its own
    statistics and fight with the imported ones over the same statistic id.
    """
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    def __init__(self, hass, coordinator, contract_id, filter_key, name, slug):
        super().__init__(coordinator)
        self.hass = hass
        self._filter = filter_key
        self._attr_name = name
        self._attr_unique_id = f"{contract_id}_{filter_key}"
        self._statistic_id = f"{DOMAIN}:{contract_id}_{slug}"
        self._statistic_name = f"Compteur 3F ({contract_id}) {name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, contract_id)},
            name=f"Compteur 3F ({contract_id})",
            manufacturer="Groupe 3F",
        )

    @property
    def native_value(self):
        """Return the latest index."""
        # Get data for this specific meter
        data = [i for i in self.coordinator.data if i.get(self._filter) is True]
        if not data: return None
        # Sort by date descending and take first
        latest = sorted(data, key=lambda x: x.get("ecrelDatrel", ""), reverse=True)[0]
        return latest.get("ecrelVal")

    @property
    def extra_state_attributes(self):
        """Attributes."""
        data = [i for i in self.coordinator.data if i.get(self._filter) is True]
        if not data: return {}
        latest = sorted(data, key=lambda x: x.get("ecrelDatrel", ""), reverse=True)[0]
        return {
            "last_reading": latest.get("ecrelDatrel"),
            "serial_number": latest.get("painsCodser", "").strip(),
            "monthly_cons_m3": latest.get("ecconVal")
        }

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self._import_historical_statistics()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._import_historical_statistics()
        super()._handle_coordinator_update()

    def _import_historical_statistics(self):
        """Import historical statistics from API data."""
        data = [i for i in self.coordinator.data if i.get(self._filter) is True]
        if not data:
            return

        # Sort by date ascending to process chronologically
        sorted_data = sorted(data, key=lambda x: x.get("ecrelDatrel", ""))

        statistics = []
        cumulative_sum = 0

        for item in sorted_data:
            date_str = item.get("ecrelDatrel")
            if not date_str:
                continue

            try:
                # Parse date (e.g., 2026-01-15T00:00:00+00:00)
                dt = datetime.fromisoformat(date_str)
                # Ensure timezone awareness
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=dt_util.UTC)

                # Use ecrelVal (meter index) as state for current reading
                meter_index = item.get("ecrelVal")
                # Use ecconVal (monthly consumption) for the incremental value
                monthly_consumption = item.get("ecconVal", 0)

                if meter_index is not None and monthly_consumption is not None:
                    # Accumulate the monthly consumption to build the sum
                    cumulative_sum += monthly_consumption

                    stat_data = {
                        "start": dt,
                        "state": meter_index,  # Current meter reading
                        "sum": cumulative_sum   # Cumulative consumption from start
                    }

                    statistics.append(StatisticData(**stat_data))
            except ValueError:
                _LOGGER.warning("Invalid date format: %s", date_str)
                continue

        if not statistics:
            return

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=self._statistic_name,
            source=DOMAIN,
            statistic_id=self._statistic_id,
            unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        )

        _LOGGER.debug("Attempting to import %d statistics for %s", len(statistics), self._statistic_id)
        async_add_external_statistics(self.hass, metadata, statistics)
        _LOGGER.info("Successfully imported %d historical statistics for %s", len(statistics), self._statistic_id)