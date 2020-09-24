from typing import List

import ipywidgets as ipw


__all__ = ("MultiCheckboxes",)


class MultiCheckboxes(ipw.Box):
    """Multiple checkboxes widget"""

    def __init__(
        self,
        values: List[bool] = None,
        descriptions: List[str] = None,
        disabled: bool = False,
        **kwargs,
    ):
        if (values and not isinstance(values, (list, tuple, set))) or (
            descriptions and not isinstance(descriptions, (list, tuple, set))
        ):
            raise TypeError("values and descriptions must be of type list")
        if values is not None:
            values = list(values)
        if descriptions is not None:
            descriptions = list(descriptions)

        if values is None and descriptions is not None:
            values = [False] * len(descriptions)
        elif values is not None and descriptions is None:
            descriptions = [f"Option {i + 1}" for i in range(len(values))]
        elif values is not None and descriptions is not None:
            if len(values) != len(descriptions):
                raise ValueError(
                    "values and descriptions must be lists of equal length."
                    f"values: {values}, descriptions: {descriptions}"
                )
        else:
            values = descriptions = []

        self._disabled = disabled

        self.checkboxes = []
        for value, description in zip(values, descriptions):
            self.checkboxes.append(
                ipw.Checkbox(
                    value=value,
                    description=description,
                    indent=False,
                    disabled=self._disabled,
                    layout={
                        "flex": "0 1 auto",
                        "width": "auto",
                        "height": "auto",
                    },
                )
            )

        super().__init__(
            children=self.checkboxes,
            layout=kwargs.get(
                "layout",
                {
                    "display": "flex",
                    "flex-flow": "row wrap",
                    "justify-content": "center",
                    "align-items": "center",
                    "align-content": "flex-start",
                    "width": "auto",
                    "height": "auto",
                },
            ),
        )

    @property
    def value(self) -> List[bool]:
        """Get list of values of checkboxes"""
        return [_.value for _ in self.checkboxes]

    @property
    def disabled(self) -> bool:
        """Whether or not the checkboxes are disabled"""
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool):
        """Set disabled value for all checkboxes"""
        if not isinstance(value, bool):
            raise TypeError("disabled must be a boolean")

        self._disabled = value
        for checkbox in self.checkboxes:
            checkbox.disabled = self._disabled
