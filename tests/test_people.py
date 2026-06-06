from custom_components.ha_groundcontrol import helpers


def test_async_get_people_exists() -> None:
    assert hasattr(helpers, "async_get_people")
    assert callable(helpers.async_get_people)
