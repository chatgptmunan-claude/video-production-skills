from pinterest_animal_dedup.analyze import analyze_pin
from pinterest_animal_dedup.models import PinMediaType, PinterestPin


def test_analyze_detects_cat_video():
    pin = PinterestPin(
        pin_id="1234567890123",
        url="https://www.pinterest.com/pin/1234567890123/",
        title="Funny cat zoomies fail",
        description="hilarious kitten",
        media_type=PinMediaType.VIDEO,
    )
    a = analyze_pin(pin)
    assert a.is_animal
    assert "cat" in a.animal_labels
    assert a.has_action
