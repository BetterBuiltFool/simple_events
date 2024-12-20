from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, overload

import pygame


# These are the types of event data we don't care about
# 'value' is a read out value, and typically analog, so we don't want that captured
# 'instance_id" is the specific joystick instace, we want to call regardless of that
# 'joy' is deprecated and can safely be ignored
_invalid_params = ["value", "instance_id", "joy"]


@dataclass
class JoyMap:
    """
    Gets a bind name from joystick event parameters
    """

    _joy_binds: dict[tuple[tuple] | None, list[str]] = field(default_factory=dict)

    @overload
    def _convert_event(self, event: dict) -> tuple[tuple]: ...

    @overload
    def _convert_event(self, event: pygame.Event) -> tuple[tuple]: ...

    def _convert_event(self, event: Any) -> tuple[tuple]:
        """
        Converts the dict of an event into a tuple of tuple suitable to use as a dict
        key.

        Ignores unneeded parameters

        :param event: pygame event, or a dict containing the data of an event.
        :return: The event's dict, converted into a tuple of tuples
        """
        event_dict: dict
        arg_type = type(event)
        if arg_type is pygame.Event:
            event_dict = event.__dict__
        elif arg_type is dict:
            event_dict = event
        else:
            raise ValueError("Invalid argument type")
        pairs: list[tuple] = []
        for key, value in event_dict.items():
            if key in _invalid_params:
                continue
            pairs.append((key, value))
        # This is a valid conversion, but Mypy doesn't like it
        return tuple(pairs)  # type: ignore

    def _convert_pairs(self, event_key: tuple[tuple]) -> dict:
        return dict((key, value) for key, value in event_key)

    def get(self, event: pygame.Event, default: Optional[list] = None) -> list[str]:
        """
        Returns the list of bind names that match the given event.

        :param event: Event generated by joystick input
        :param default: Return value if no binds match the event, defaults to None
        :return: A list of bind names, or the given default value, or None
        :raises ValueError: Raised if the bind name is not found.
        """
        # Convert the dict of an event into a tuple of tuple to use as a dict key
        key = self._convert_event(event)
        if default is None:
            default = []
        return self._joy_binds.get(key, default)

    def get_bound_joystick_event(self, bind_name: str) -> dict | None:
        """
        Returns joystick event data that a bind is tied to.
        If a bind exists but is unbound, returns None

        :param bind_name: Name of target bind
        :raises ValueError: If bind_name is not found
        :return: dict containing joystick event data, or None if unbound
        """
        for key, bind_list in self._joy_binds.items():
            if bind_name in bind_list:
                if key is None:
                    return key
                return self._convert_pairs(key)
        raise ValueError(f"Bind name: {bind_name} not found.")

    def generate_bind(
        self, bind_name: str, default_joystick_data: Optional[dict] = None
    ) -> None:
        try:
            self.get_bound_joystick_event(bind_name)
        except ValueError:
            self._joy_binds.setdefault(
                # adds the bind to joy_binds, under the given parameters
                (
                    self._convert_event(default_joystick_data)
                    if default_joystick_data is not None
                    else None
                ),
                [],
            ).append(bind_name)

    def _rebind(
        self, bind_name: str, new_joystick_data: Optional[tuple[tuple]] = None
    ) -> None:
        self.remove_bind(bind_name)
        self._joy_binds.setdefault(new_joystick_data, []).append(bind_name)

    def rebind(self, bind_name: str, new_joystick_data: Optional[dict] = None):
        """
        Converts a bind from its current expected data to the new data for matching.

        :param bind_name: he name of the bind whose calling event is changing.
        :param new_joystick_data: The new joystick event data, defaults to None.
        If none, the bind name is considered unbound, and will not be called by notify()
        """
        self._rebind(
            bind_name,
            (
                self._convert_event(new_joystick_data)
                if new_joystick_data is not None
                else None
            ),
        )

    def remove_bind(self, bind_name: str) -> None:
        """
        Clears the given bind from all joystick inputs.

        :param bind_name: Name of the target bind
        """
        dead_keys = []
        for key, bind_list in self._joy_binds.items():
            if bind_name in bind_list:
                bind_list.remove(bind_name)
            if len(bind_list) == 0:
                dead_keys.append(key)
        for key in dead_keys:
            self._joy_binds.pop(key)

    def merge(self, other: JoyMap) -> None:
        """
        Combines two JoyBinds, adding any new binds from the latter and updating
        overlapping binds to match the latter, while preserving any unique binds

        :param other: A JoyMap with preferred binds.
        """
        for joy_data, bind_list in other._joy_binds.items():
            for bind in bind_list:
                self._rebind(bind, joy_data)

    def pack_binds(self) -> dict:
        """
        Converts the dictionary of binds and their needed inputs into a saveable dict,
        with the bind name forward for manual remapping in a file
        """
        packed_dict: dict[str, tuple[tuple] | None] = {}
        for joy_data, bind_list in self._joy_binds.items():
            for bind in bind_list:
                packed_dict.update({bind: joy_data})

        return packed_dict
