# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Implements various generic attrs validators.
"""

import warnings
from enum import Enum
from typing import Any, List, Type

import attr
from attr import Attribute, attrs


@attrs(repr=False, slots=True, hash=True)
class _EnumValidator:
    """Validator for use by enum(), following the pattern from the standard attrs _InValidator."""

    options = attr.ib(type=Type[Enum])

    def __call__(self, instance: Any, attribute: Attribute, value: Enum) -> None:  # type: ignore
        try:
            # This gives us "DeprecationWarning: using non-Enums in containment checks will raise TypeError in Python 3.8"
            # Uh, yeah.  I know.  I'm catching TypeError.  And anyway, this method is restricted to enums.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                in_options = value in self.options
        except TypeError:
            in_options = False
        if not in_options:
            legal = ", ".join(sorted([option.name for option in list(self.options)]))  # type: ignore
            raise ValueError("'%s' must be one of [%s]" % (attribute.name, legal))


@attrs(repr=False, slots=True, hash=True)
class _LengthValidator:
    """Validator for use by maxlength(), following the pattern from the standard attrs _InValidator."""

    maxlength = attr.ib(type=int)

    def __call__(self, instance: Any, attribute: Attribute, value: str) -> None:  # type: ignore
        if len(value) > self.maxlength:
            raise ValueError("'%s' must not exceed length %d" % (attribute.name, self.maxlength))


def enum(options: Type[Enum]) -> _EnumValidator:
    """attrs validator to ensure that a value is a legal enumeration."""
    return _EnumValidator(options)


def length(maxlength: int) -> _LengthValidator:
    """attrs validator to ensure that a string value does not exceed a length."""
    return _LengthValidator(maxlength)


def notempty(_instance: Any, attribute: Attribute, value: Any) -> None:  # type: ignore
    """attrs validator to ensure that a list is not empty."""
    if len(value) == 0:
        raise ValueError("'%s' may not be empty" % attribute.name)


def string(_instance: Any, attribute: Attribute, value: str) -> None:  # type: ignore
    """attrs validator to ensure that a string is non-empty."""
    # Annoyingly, due to some quirk in the CattrConverter, we end up with "None" rather than None for strings set to JSON null
    # As a result, we need to prevent "None" as a legal value, but that's probably better anyway.
    if value is None or value == "None" or not isinstance(value, str) or len(value) == 0:
        raise ValueError("'%s' must be a non-empty string" % attribute.name)


def stringlist(_instance: Any, attribute: Attribute, value: List[str]) -> None:  # type: ignore
    """attrs validator to ensure that a string list contains non-empty values."""
    # Annoyingly, due to some quirk in the CattrConverter, we end up with "None" rather than None for strings set to JSON null
    # As a result, we need to prevent "None" as a legal value, but that's probably better anyway.
    for element in value:
        if element is None or element == "None" or not isinstance(element, str) or len(element) == 0:
            raise ValueError("'%s' elements must be non-empty strings" % attribute.name)
