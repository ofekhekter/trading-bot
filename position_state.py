import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class PositionStateStore:
    """
    Persistent state for open positions.

    The file is written atomically so a crash during save is less likely
    to corrupt the previous valid state.
    """

    def __init__(
        self,
        file_path: str = "position_state.json",
    ):
        self.file_path = Path(file_path)

    def _load_all(self) -> Dict[str, Any]:
        if not self.file_path.exists():
            return {}

        try:
            with self.file_path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                data = json.load(handle)

        except (
            json.JSONDecodeError,
            OSError,
        ) as exc:
            raise RuntimeError(
                f"Could not read position state "
                f"from {self.file_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(
                "Position state file is invalid."
            )

        return data

    def get(
        self,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        data = self._load_all()

        state = data.get(
            symbol.upper()
        )

        if state is None:
            return None

        if not isinstance(state, dict):
            raise RuntimeError(
                f"Invalid state for {symbol.upper()}."
            )

        return state

    def save(
        self,
        symbol: str,
        state: Dict[str, Any],
    ) -> None:
        symbol = symbol.upper()

        data = self._load_all()

        state_to_save = dict(state)
        state_to_save["symbol"] = symbol
        state_to_save["updated_at_utc"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        data[symbol] = state_to_save

        temp_path = self.file_path.with_suffix(
            self.file_path.suffix + ".tmp"
        )

        try:
            with temp_path.open(
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    data,
                    handle,
                    indent=2,
                    sort_keys=True,
                )

            os.replace(
                temp_path,
                self.file_path,
            )

        except OSError as exc:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            raise RuntimeError(
                f"Could not save position state "
                f"to {self.file_path}: {exc}"
            ) from exc

    def remove(
        self,
        symbol: str,
    ) -> None:
        symbol = symbol.upper()

        data = self._load_all()

        if symbol not in data:
            return

        del data[symbol]

        temp_path = self.file_path.with_suffix(
            self.file_path.suffix + ".tmp"
        )

        try:
            with temp_path.open(
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    data,
                    handle,
                    indent=2,
                    sort_keys=True,
                )

            os.replace(
                temp_path,
                self.file_path,
            )

        except OSError as exc:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            raise RuntimeError(
                f"Could not update position state "
                f"in {self.file_path}: {exc}"
            ) from exc
