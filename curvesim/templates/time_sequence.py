"""Interfaces for TimeSequences, used to track time within simulations."""


from datetime import datetime, timezone
from typing import Generic, Iterable, Optional, TypeVar, Union

from pandas import DateOffset, date_range
from pandas.tseries.frequencies import to_offset

from curvesim.exceptions import TimeSequenceError

T = TypeVar("T")


class TimeSequence(Generic[T]):
    """
    Generic class for time-like sequences.
    Abstraction to encompass different ways of tracking "time",
    useful for trading strategies involving a blockchain.
    This could be timestamps, block times, block numbers, etc.
    """

    def __init__(self, sequence: Iterable[T]):
        _validate_sequence(sequence)
        self._sequence = tuple(sequence)

    def __getitem__(self, index):
        return self._sequence[index]

    def __iter__(self):
        for time in self._sequence:
            yield time

    def __len__(self):
        return len(self._sequence)

    def __repr__(self):
        return f"<{self.__class__.__name__} start={self[0]} end={self[-1]}>"


class DateTimeSequence(TimeSequence[datetime]):
    """
    TimeSequence composed of datetimes.
    """

    def __init__(
        self,
        sequence: Iterable[datetime],
        freq: Optional[Union[str, DateOffset]] = None,
    ):
        _validate_datetime_sequence(sequence)
        super().__init__(sequence)
        self.freq = to_offset(freq)

    @classmethod
    def from_range(
        cls,
        *,
        start=None,
        end=None,
        periods=None,
        freq=None,
        tz=timezone.utc,
        inclusive="both",
        unit=None,
    ):
        """
        Instantiates a DateTimeSequence from a pandas date range.
        The function signature is analogous to pandas.date_range.
        """

        times = date_range(
            start=start,
            end=end,
            periods=periods,
            freq=freq,
            tz=tz,
            inclusive=inclusive,
            unit=unit,
        )

        return cls(times, freq=times.freq)


def _validate_sequence(times):
    if not isinstance(times, Iterable) or isinstance(times, str):
        type_name = type(times).__name__
        raise TimeSequenceError(
            f"Input time sequence must be a non-string iterable, not '{type_name}'."
        )

    if sorted(times) != list(times):
        raise TimeSequenceError("Input time sequence must be in ascending order.")

    if len(set(times)) != len(times):
        raise TimeSequenceError("Input time sequence must not contain duplicates.")


def _validate_datetime_sequence(times):
    if not all(isinstance(t, datetime) for t in times):
        raise TimeSequenceError(
            "DateTimeSequence may only contain iterables of datetime.datetime."
        )
