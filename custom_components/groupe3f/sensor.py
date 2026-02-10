"""Sensor platform for Groupe 3F."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics,
)
from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass
)
from homeassistant.const import UnitOfVolume
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
    # Map JSON boolean keys to Names
    types = {"compteurChaud": "Eau Chaude", "compteurFroid": "Eau Froide"}

    for key, name in types.items():
        # Check if any data exists for this meter type
        if any(item.get(key) is True for item in coordinator.data):
            entities.append(Groupe3FSensor(hass, coordinator, contract_id, key, name))

    async_add_entities(entities)

class Groupe3FSensor(CoordinatorEntity, SensorEntity):
    """Groupe 3F Sensor."""
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    def __init__(self, hass, coordinator, contract_id, filter_key, name):
        super().__init__(coordinator)
        self.hass = hass
        self._filter = filter_key
        self._attr_name = name
        self._attr_unique_id = f"{contract_id}_{filter_key}"
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

    async def _update_callback(self) -> None:
        """Handle update."""
        await super()._update_callback()
        self._import_historical_statistics()

    def _import_historical_statistics(self):
        """Import historical statistics from API data."""
        data = [i for i in self.coordinator.data if i.get(self._filter) is True]
        if not data:
            return

        # Sort by date ascending to process chronologically
        sorted_data = sorted(data, key=lambda x: x.get("ecrelDatrel", ""))
        
        statistics = []
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
                
                total_val = item.get("ecrelVal")
                
                if total_val is not None:
                    statistics.append(
                        StatisticData(
                            start=dt,
                            state=total_val,
                            sum=total_val
                        )
                    )
            except ValueError:
                _LOGGER.warning("Invalid date format: %s", date_str)
                continue

        if not statistics:
            return

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=self.name,
            source=DOMAIN,
            statistic_id=self.entity_id,
            unit_of_measurement=self.native_unit_of_measurement,
        )

        async_import_statistics(self.hass, metadata, statistics)
        _LOGGER.debug("Imported %d statistics for %s", len(statistics), self.entity_id)