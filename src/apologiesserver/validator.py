# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:
# pylint: disable=unsubscriptable-object

"""
Implements various generic attrs validators.
"""

import warnings
from enum import Enum
from typing import Any, Sequence, Type

import attr
from attr import Attribute, attrs


@attrs(repr=False, slots=True, hash=True)
class _EnumValidator:
    """Validator for use by enum(), following the pattern from the standard attrs _InValidator."""

    options = attr.ib(type=Type[Enum])

    def __call__(self, instance: Any, attribute: Attribute, value: Enum) -> None:  # type: ignore
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                in_options = value in self.options
        except TypeError:
            in_options = False
        if not in_options:
            legal = ", ".join(sorted([option.name for option in list(self.options)]))  # type: ignore
            raise ValueError("'%s' must be one of [%s]" % (attribute.name, legal))


def enum(options: Type[Enum]) -> _EnumValidator:
    """attrs validator to ensure that a value is a legal enumeration."""
    return _EnumValidator(options)


def notempty(instance: Any, attribute: Attribute, value: Any) -> None:  # type: ignore
    """attrs validator to ensure that a list is not empty."""
    if len(value) == 0:
        raise ValueError("'%s' may not be empty" % attribute.name)


def string(instance: Any, attribute: Attribute, value: str) -> None:  # type: ignore
    """attrs validator to ensure that a string is non-empty."""
    # Annoyingly, due to some quirk in the CattrConverter, we end up with "None" rather than None for strings set to JSON null
    # As a result, we need to prevent "None" as a legal value, but that's probably better anyway.
    if value is None or value == "None" or not isinstance(value, str) or len(value) == 0:
        raise ValueError("'%s' must be a non-empty string" % attribute.name)


def stringlist(instance: Any, attribute: Attribute, value: Sequence[str]) -> None:  # type: ignore
    """attrs validator to ensure that a string list contains non-empty values."""
    # Annoyingly, due to some quirk in the CattrConverter, we end up with "None" rather than None for strings set to JSON null
    # As a result, we need to prevent "None" as a legal value, but that's probably better anyway.
    for element in value:
        if element is None or element == "None" or not isinstance(element, str) or len(element) == 0:
            raise ValueError("'%s' elements must be non-empty strings" % attribute.name)
