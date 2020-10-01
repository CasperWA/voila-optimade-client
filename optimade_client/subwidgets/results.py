import typing
from urllib.parse import urlparse, parse_qs

import ipywidgets as ipw
import traitlets

from optimade_client.exceptions import InputError
from optimade_client.logger import LOGGER


__all__ = ("StructureDropdown", "ResultsPageChooser")


class StructureDropdown(ipw.Dropdown):
    """Dropdown for showing structure results"""

    NO_OPTIONS = "Search for structures ..."
    HINT = "Select a structure"

    def __init__(self, options=None, **kwargs):
        if options is None:
            options = [(self.NO_OPTIONS, None)]
        else:
            options.insert(0, (self.HINT, None))

        super().__init__(options=options, **kwargs)

    def set_options(self, options: list):
        """Set options with hint at top/as first entry"""
        options.insert(0, (self.HINT, None))
        self.options = options
        with self.hold_trait_notifications():
            self.index = 0

    def reset(self):
        """Reset widget"""
        with self.hold_trait_notifications():
            self.options = [(self.NO_OPTIONS, None)]
            self.index = 0
            self.disabled = True

    def freeze(self):
        """Disable widget"""
        self.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.disabled = False


class ResultsPageChooser(ipw.HBox):  # pylint: disable=too-many-instance-attributes
    """Flip through the OPTIMADE 'pages'

    NOTE: Only supports offset-pagination at the moment.
    """

    page_offset = traitlets.Int(None, allow_none=True)
    page_number = traitlets.Int(None, allow_none=True)
    page_link = traitlets.Unicode(allow_none=True)

    # {name: default value}
    SUPPORTED_PAGEING = {"page_offset": 0, "page_number": 1}

    def __init__(self, page_limit: int, **kwargs):
        self._cache = {}
        self.__last_page_offset: typing.Union[None, int] = None
        self.__last_page_number: typing.Union[None, int] = None
        self._layout = ipw.Layout(width="auto")

        self._page_limit = page_limit
        self._data_returned = 0
        self._data_available = 0
        self.pages_links = {}

        self._button_layout = {
            "style": ipw.ButtonStyle(button_color="white"),
            "layout": ipw.Layout(width="auto"),
        }
        self.button_first = self._create_arrow_button(
            "angle-double-left", "First results"
        )
        self.button_prev = self._create_arrow_button(
            "angle-left", f"Previous {self._page_limit} results"
        )
        self.text = ipw.HTML("Showing 0 of 0 results")
        self.button_next = self._create_arrow_button(
            "angle-right", f"Next {self._page_limit} results"
        )
        self.button_last = self._create_arrow_button(
            "angle-double-right", "Last results"
        )

        self.button_first.on_click(self._goto_first)
        self.button_prev.on_click(self._goto_prev)
        self.button_next.on_click(self._goto_next)
        self.button_last.on_click(self._goto_last)

        self._update_cache()

        super().__init__(
            children=[
                self.button_first,
                self.button_prev,
                self.text,
                self.button_next,
                self.button_last,
            ],
            layout=self._layout,
            **kwargs,
        )

    @traitlets.validate("page_offset")
    def _set_minimum_page_offset(self, proposal):  # pylint: disable=no-self-use
        """Must be >=0. Set value to 0 if <0."""
        value = proposal["value"]
        if value < 0:
            value = 0
        return value

    @traitlets.validate("page_number")
    def _set_minimum_page_number(self, proposal):  # pylint: disable=no-self-use
        """Must be >=1. Set value to 1 if <1."""
        value = proposal["value"]
        if value < 1:
            value = 1
        return value

    def reset(self):
        """Reset widget"""
        self.button_first.disabled = True
        self.button_prev.disabled = True
        self.text.value = "Showing 0 of 0 results"
        self.button_next.disabled = True
        self.button_last.disabled = True
        with self.hold_trait_notifications():
            self.page_offset = self.SUPPORTED_PAGEING["page_offset"]
            self.page_number = self.SUPPORTED_PAGEING["page_number"]
            self.page_link = None
        self._update_cache()

    def freeze(self):
        """Disable widget"""
        self.button_first.disabled = True
        self.button_prev.disabled = True
        self.button_next.disabled = True
        self.button_last.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.button_first.disabled = self._cache["buttons"]["first"]
        self.button_prev.disabled = self._cache["buttons"]["prev"]
        self.button_next.disabled = self._cache["buttons"]["next"]
        self.button_last.disabled = self._cache["buttons"]["last"]

    @property
    def data_returned(self) -> int:
        """Total number of entities"""
        return self._data_returned

    @data_returned.setter
    def data_returned(self, value: int):
        """Set total number of entities"""
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise InputError("data_returned must be an integer") from exc
        else:
            self._data_returned = value

    @property
    def data_available(self) -> int:
        """Total number of entities available"""
        return self._data_available

    @data_available.setter
    def data_available(self, value: int):
        """Set total number of entities available"""
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise InputError("data_available must be an integer") from exc
        else:
            self._data_available = value

    @property
    def _last_page_offset(self) -> int:
        """Get the page_offset for the last page"""
        if self.__last_page_offset is not None:
            return self.__last_page_offset

        if self.data_returned <= self._page_limit:
            res = 0
        elif self.data_returned % self._page_limit == 0:
            res = self.data_returned - self._page_limit
        else:
            res = self.data_returned - self.data_returned % self._page_limit

        self.__last_page_offset = res
        return self.__last_page_offset

    @property
    def _last_page_number(self) -> int:
        """Get the page_number for the last page"""
        if self.__last_page_number is not None:
            return self.__last_page_number

        self.__last_page_number = int(self.data_available / self._page_limit)
        self.__last_page_number += 1 if self.data_available % self._page_limit else 0

        return self.__last_page_number

    def _update_cache(self, page_offset: int = None, page_number: int = None):
        """Update cache"""
        offset = page_offset if page_offset is not None else self.page_offset
        number = page_number if page_number is not None else self.page_number
        self._cache = {
            "buttons": {
                "first": self.button_first.disabled,
                "prev": self.button_prev.disabled,
                "next": self.button_next.disabled,
                "last": self.button_last.disabled,
            },
            "page_offset": offset,
            "page_number": number,
        }

    def _create_arrow_button(self, icon: str, hover_text: str = None) -> ipw.Button:
        """Create an arrow button"""
        tooltip = hover_text if hover_text is not None else ""
        return ipw.Button(
            disabled=True, icon=icon, tooltip=tooltip, **self._button_layout
        )

    def _parse_pageing(self, url: str, pageing: str = "page_offset") -> int:
        """Retrieve and parse `pageing` value from request URL"""
        parsed_url = urlparse(url)
        query = parse_qs(parsed_url.query)
        return int(query.get(pageing, [str(self.SUPPORTED_PAGEING[pageing])])[0])

    def _goto_first(self, _):
        """Go to first page of results"""
        if self.pages_links.get("first", False):
            for pageing in self.SUPPORTED_PAGEING:
                self._cache[pageing] = self._parse_pageing(
                    self.pages_links["first"], pageing
                )

            LOGGER.debug(
                "Go to first page of results - using link: %s",
                self.pages_links["first"],
            )
            self.page_link = self.pages_links["first"]
        else:
            self._cache["page_offset"] = 0
            self._cache["page_number"] = 1

            LOGGER.debug(
                "Go to first page of results - using pageing:\n  page_offset=%d\n  page_number=%d",
                self._cache["page_offset"],
                self._cache["page_number"],
            )
            self.page_offset = self._cache["page_offset"]
            self.page_number = self._cache["page_number"]

    def _goto_prev(self, _):
        """Go to previous page of results"""
        if self.pages_links.get("prev", False):
            for pageing in self.SUPPORTED_PAGEING:
                self._cache[pageing] = self._parse_pageing(
                    self.pages_links["prev"], pageing
                )

            LOGGER.debug(
                "Go to previous page of results - using link: %s",
                self.pages_links["prev"],
            )
            self.page_link = self.pages_links["prev"]
        else:
            self._cache["page_offset"] -= self._page_limit
            self._cache["page_number"] -= 1

            LOGGER.debug(
                "Go to previous page of results - using pageing:\n  page_offset=%d\n  "
                "page_number=%d",
                self._cache["page_offset"],
                self._cache["page_number"],
            )
            self.page_offset = self._cache["page_offset"]
            self.page_number = self._cache["page_number"]

    def _goto_next(self, _):
        """Go to next page of results"""
        if self.pages_links.get("next", False):
            for pageing in self.SUPPORTED_PAGEING:
                self._cache[pageing] = self._parse_pageing(
                    self.pages_links["next"], pageing
                )

            LOGGER.debug(
                "Go to next page of results - using link: %s", self.pages_links["next"]
            )
            self.page_link = self.pages_links["next"]
        else:
            self._cache["page_offset"] += self._page_limit
            self._cache["page_number"] += 1

            LOGGER.debug(
                "Go to next page of results - using pageing:\n  page_offset=%d\n  page_number=%d",
                self._cache["page_offset"],
                self._cache["page_number"],
            )
            self.page_offset = self._cache["page_offset"]
            self.page_number = self._cache["page_number"]

    def _goto_last(self, _):
        """Go to last page of results"""
        if self.pages_links.get("last", False):
            for pageing in self.SUPPORTED_PAGEING:
                self._cache[pageing] = self._parse_pageing(
                    self.pages_links["last"], pageing
                )

            LOGGER.debug(
                "Go to last page of results - using link: %s", self.pages_links["last"]
            )
            self.page_link = self.pages_links["last"]
        else:
            self._cache["page_offset"] = self._last_page_offset
            self._cache["page_number"] = self._last_page_number

            LOGGER.debug(
                "Go to last page of results - using offset: %d",
                self._cache["page_offset"],
            )
            self.page_offset = self._cache["page_offset"]

    def _update(self):
        """Update widget according to chosen results using pageing"""
        offset = self._cache["page_offset"]
        number = self._cache["page_number"]

        if offset >= self._page_limit or number > self.SUPPORTED_PAGEING["page_number"]:
            self.button_first.disabled = False
            self.button_prev.disabled = False
        else:
            self.button_first.disabled = True
            self.button_prev.disabled = True

        if self.data_returned > self._page_limit:
            if offset == self._last_page_offset or number == self._last_page_number:
                result_range = f"{offset + 1}-{self.data_returned}"
            else:
                result_range = f"{offset + 1}-{offset + self._page_limit}"
        elif self.data_returned == 0:
            result_range = "0"
        elif self.data_returned == 1:
            result_range = "1"
        else:
            result_range = f"{offset + 1}-{self.data_returned}"
        self.text.value = f"Showing {result_range} of {self.data_returned} results"

        if offset == self._last_page_offset or number == self._last_page_number:
            self.button_next.disabled = True
            self.button_last.disabled = True
        else:
            self.button_next.disabled = False
            self.button_last.disabled = False

        self._update_cache(page_offset=offset, page_number=number)

    def set_pagination_data(
        self,
        data_returned: int = None,
        data_available: int = None,
        links_to_page: dict = None,
        reset_cache: bool = False,
    ):
        """Set data needed to 'activate' this pagination widget"""
        if data_returned is not None:
            self.data_returned = data_returned
        if data_available is not None:
            self.data_available = data_available
        if links_to_page is not None:
            self.pages_links = links_to_page
        if reset_cache:
            self._update_cache(**self.SUPPORTED_PAGEING)
            self.__last_page_offset = None

        self._update()

    def update_offset(self) -> int:
        """Update offset from cache"""
        with self.hold_trait_notifications():
            self.page_offset = self._cache["page_offset"]

    def silent_reset(self):
        """Reset, but avoid updating page_offset or page_link"""
        self.set_pagination_data(data_returned=0, links_to_page=None, reset_cache=True)
