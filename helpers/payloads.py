"""Request encoders shared by booking creation and update tests."""

from typing import Any
from xml.etree import ElementTree


def xml_payload(payload: dict[str, Any]) -> str:
    """Serialize valid booking fields as an XML request body.

    Args:
        payload: Complete booking data.

    Returns:
        str: XML document with escaped text values.
    """
    root = ElementTree.Element('booking')
    for name, value in payload.items():
        element = ElementTree.SubElement(root, name)
        if isinstance(value, dict):
            for key, text in value.items():
                ElementTree.SubElement(element, key).text = str(text)
        elif isinstance(value, bool):
            element.text = str(value).lower()
        else:
            element.text = str(value)
    return ElementTree.tostring(root, encoding='unicode')


def form_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten booking dates for a form-urlencoded request.

    Args:
        payload: Complete booking data.

    Returns:
        dict[str, Any]: Fields with bracket notation for nested dates.
    """
    result = {key: value for key, value in payload.items() if key != 'bookingdates'}
    result['depositpaid'] = str(payload['depositpaid']).lower()
    result.update({f'bookingdates[{key}]': value for key, value in payload['bookingdates'].items()})
    return result
