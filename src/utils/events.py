from collections import defaultdict
from typing import Any, Callable, Dict, List, Type, TypeVar

T = TypeVar("T")

_DEBUG = False


class EventManager:
    """Global Event Dispatcher / Pub-Sub System."""

    def __init__(self) -> None:
        self._listeners: Dict[Any, List[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event_type: Any, callback: Callable[..., Any]) -> None:
        """Subscribe a callback function to a specific event topic or class.

        :param event_type: A string channel name (e.g. 'config_updated') or a
        class type.
        :param callback: The function to execute when triggered.
        """
        if _DEBUG: print(f'---events.subscribe {event_type} -> {callable}')
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: Any, callback: Callable[..., Any]) -> None:
        """Remove a subscribed callback from an event topic."""
        if _DEBUG: print(f'---events.unsubscribe {event_type} -> {callable}')
        if callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)

    def dispatch(self, event_type: Any, *args: Any, **kwargs: Any) -> None:
        """Trigger/dispatch an event, executing all subscribed callbacks with

        the given parameters.
        """
        if _DEBUG: print(f'---events.dispatch {event_type} -> args: {args}, kwargs: {kwargs}')
        # Iterate over a shallow copy to allow subscribers to safely unsubscribe mid-event
        for callback in list(self._listeners.get(event_type, [])):
            callback(*args, **kwargs)

    # Alias methods for alternative naming preferences
    on = subscribe
    off = unsubscribe
    trigger = dispatch

def listen(self, event_type: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register an event subscriber."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        self.subscribe(event_type, func)
        return func

    return decorator


# Add method to instance or class
EventManager.listen = listen

# Global single instance
events = EventManager()


def _test_string_key():
    # 1. Define subscriber callbacks
    def handle_config_change(new_config: dict) -> None:
        print(f"[Config Listener] Updated: {new_config}")


    def handle_ui_refresh(new_config: dict) -> None:
        print("[UI Listener] Redrawing UI elements...")


    # 2. Subscribe using 'subscribe' or 'on'
    events.subscribe("config.updated", handle_config_change)
    events.on("config.updated", handle_ui_refresh)

    # 3. Trigger / Dispatch from anywhere in your codebase
    events.dispatch("config.updated", {"theme": "dark", "font_size": 14})
    # Or: events.trigger('config.updated', ...)

    # 4. Unsubscribe
    events.unsubscribe("config.updated", handle_ui_refresh)


def _test_class_key():
    from dataclasses import dataclass

    @dataclass
    class CardReviewedEvent:
        card_id: int
        ease: int
        interval: int


    # Subscribe directly to the Event Class
    def on_card_reviewed(event: CardReviewedEvent) -> None:
        print(
            f"Card {event.card_id} reviewed with ease {event.ease}. New IVL: {event.interval}"
        )


    events.subscribe(CardReviewedEvent, on_card_reviewed)

    # Dispatch an instance of the event
    payload = CardReviewedEvent(card_id=162001, ease=3, interval=12)
    events.dispatch(CardReviewedEvent, payload)


def _test_decorator():
    # Usage:
    @events.listen("profile_loaded")
    def on_profile_loaded(profile_name: str) -> None:
        print(f"Profile {profile_name} loaded!")


if __name__ == '__main__':
    _test_string_key()
    _test_class_key()
    _test_decorator()
