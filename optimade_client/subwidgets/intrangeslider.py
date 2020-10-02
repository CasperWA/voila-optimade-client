from typing import Tuple, Union

from ipywidgets import IntRangeSlider


class CustomIntRangeSlider(IntRangeSlider):
    """An IntRangeSlider that will not return values if equal to min/max"""

    def get_value(self) -> Tuple[Union[int, None], Union[int, None]]:
        """Retrieve value, making them `None` if they're equal to the extremas."""
        min_ = None if self.min == self.value[0] else self.value[0]
        max_ = None if self.max == self.value[1] else self.value[1]
        return min_, max_
