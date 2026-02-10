"""API Client for Groupe 3F."""
import logging
import uuid
from typing import Any, Dict, List, Optional

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "3f-version-app": "2.3.4",
}

class Groupe3FApi:
    """API Client to handle communication with Groupe 3F."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._token: Optional[str] = None
        self._username: Optional[str] = None
        # Generate a unique ID to simulate a persistent device
        self._trusted_id = str(uuid.uuid4())

    def set_credentials(self, token: str, trusted_id: str) -> None:
        """Set credentials from storage."""
        self._token = token
        if trusted_id:
            self._trusted_id = trusted_id

    def get_trusted_id(self) -> str:
        return self._trusted_id

    async def login(self, username, password) -> Dict[str, Any]:
        """Attempt to login."""
        self._username = username
        url = f"{BASE_URL}/login"
        payload = {
            "username": username,
            "password": password,
            "data": {"trusted": self._trusted_id}
        }

        try:
            async with self._session.post(url, json=payload, headers=DEFAULT_HEADERS) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if "token" in data:
                    self._token = data["token"]
                    return {"status": "success", "data": data}

                if data.get("message") == "2FA_REQUIRED":
                    return {"status": "2fa_required"}

                return {"status": "error", "message": "Unknown response"}
        except Exception as error:
            _LOGGER.error("Login failed: %s", error)
            raise

    async def check_2fa(self, code: str) -> Dict[str, Any]:
        """Validate 2FA code."""
        url = f"{BASE_URL}/login/2fa_check"
        payload = {
            "data": {
                "authCode": code,
                "trusted": self._trusted_id
            }
        }

        async with self._session.post(url, json=payload, headers=DEFAULT_HEADERS) as resp:
            resp.raise_for_status()
            data = await resp.json()
            if "token" in data:
                self._token = data["token"]
                return {"status": "success", "data": data}
            raise Exception("Invalid 2FA response")

    async def get_caint_num(self) -> str:
        """Fetch the caintNum (allocataire number)."""
        if not self._username:
            raise Exception("Username not set")
            
        url = f"{BASE_URL}/comptes"
        params = {"email": self._username}
        headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {self._token}"}

        async with self._session.get(url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            
            if isinstance(data, list) and len(data) > 0:
                # Navigate through the structure: [0] -> clients -> [0] -> caintNum
                account = data[0]
                if "clients" in account and isinstance(account["clients"], list) and len(account["clients"]) > 0:
                    return str(account["clients"][0]["caintNum"])
            
            raise Exception("No caintNum found in account data")

    async def get_contract_id(self) -> str:
        """Fetch the first available contract ID from summary."""
        caint_num = await self.get_caint_num()
        
        url = f"{BASE_URL}/sommaires"
        params = {"caint_num": caint_num}
        headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {self._token}"}

        async with self._session.get(url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()

            if isinstance(data, list) and len(data) > 0:
                return str(data[0]["contratId"])
            raise Exception("No contracts found")

    async def get_water_consumption(self, contract_id: str) -> List[Dict[str, Any]]:
        """Fetch consumption data."""
        url = f"{BASE_URL}/contrats/{contract_id}/eau_consos"
        headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {self._token}"}

        async with self._session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()