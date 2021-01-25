import logging
import os
from pathlib import Path
import shutil
from typing import Union
from urllib.parse import urlencode

import ipywidgets as ipw

from optimade_client.logger import LOG_DIR, LOGGER, REPORT_HANDLER, WIDGET_HANDLER
from optimade_client.utils import __optimade_version__, ButtonStyle, CACHE_DIR


IMG_DIR = Path(__file__).parent.joinpath("img")
SOURCE_URL = "https://github.com/CasperWA/voila-optimade-client/"


class HeaderDescription(ipw.VBox):
    """Top logo and description of the OPTIMADE Client

    Special buttons are needed for reporting, hence HTML widgets are instantiated.
    Each button is also different from each other, hence the templates below are either
    HTML-encoded or not.
    The bug report button utilizes the special REPORT_LOGGER, which stays below a certain maximum
    number of bytes-length (of logs), in order to not surpass the allowed URL length for GitHub and
    get an errornous 414 response.
    After some testing I am estimating the limit to be at 8 kB.
    The suggestion report button utilizes instead the HTML Form element to "submit" the GitHub issue
    template. While an actual markdown template could be used, it seems GitHub is coercing its users
    to create these templates via their GUI and the documentation for creating them directly in the
    repository is disappearing. Hence, I have chosen to use templates in this manner instead, where
    I have more control over them.
    """

    HEADER = f"""<p style="font-size:14px;">
<b>Currently valid OPTIMADE API version</b>: <code>v{__optimade_version__[0]}</code><br>
<b>Client version</b>: <code>2021.1.25</code><br>
<b>Source code</b>: <a href="{SOURCE_URL}" target="_blank">GitHub</a>
</p>
"""
    DESCRIPTION = f"""<p style="line-height:1.5;font-size:14px;">
This is a friendly client to search through databases and other implementations exposing an OPTIMADE RESTful API.
To get more information about the OPTIMADE API,
please see <a href="https://www.optimade.org/" target="_blank">the offical web page</a>.
All providers are retrieved from <a href="https://providers.optimade.org/" target="_blank">the OPTIMADE consortium's list of providers</a>.
</p>
<p style="line-height:1.5;font-size:14px;margin-top:5px;">
<i>Note</i>: The structure property <code>assemblies</code> is currently not supported.
Follow <a href="{SOURCE_URL}issues/12" target="_blank">the issue on GitHub</a> to learn more.
</p>
"""
    BUG_TEMPLATE = {
        "title": "[BUG] - TITLE",
        "body": (
            "## Bug description\n\nWhat happened?\n\n"
            "### Expected behaviour (optional)\n\nWhat should have happened?\n\n"
            "### Actual behavior (optional)\n\nWhat happened instead?\n\n"
            "## Reproducibility (optional)\n\nHow may it be reproduced?\n\n"
            "### For developers (do not alter this section)\n"
        ),
    }
    SUGGESTION_TEMPLATE = {
        "title": "[FEATURE/CHANGE] - TITLE",
        "body": (
            "## Feature/change description\n\n"
            "What should it be able to do? Or what should be changed?\n\n"
            "### Reasoning (optional)\n\n"
            "Why is this feature or change needed?"
        ),
    }

    def __init__(
        self, logo: str = None, button_style: Union[ButtonStyle, str] = None, **kwargs
    ):
        logo = logo if logo is not None else "optimade-text-right-transparent-bg.png"
        logo = self._get_file(str(IMG_DIR.joinpath(logo)))
        logo = ipw.Image(value=logo, format="png", width=375, height=137.5)

        if button_style:
            if isinstance(button_style, str):
                button_style = ButtonStyle[button_style.upper()]
            elif isinstance(button_style, ButtonStyle):
                pass
            else:
                raise TypeError(
                    "button_style should be either a string or a ButtonStyle Enum. "
                    f"You passed type {type(button_style)!r}."
                )
        else:
            button_style = ButtonStyle.DEFAULT

        header = ipw.HTML(self.HEADER)

        # Hidden input HTML element, storing the log
        self._debug_log = REPORT_HANDLER.get_widget()
        self.report_bug = ipw.HTML(
            f"""
<button type="button" class="p-Widget jupyter-widgets jupyter-button widget-button mod-{button_style.value}"
title="Create a bug issue on GitHub that includes a log file" style="width:auto;"
onclick="
var log = document.getElementById('{self._debug_log.element_id}');

var link = document.createElement('a');
link.target = '_blank';
link.href = '{SOURCE_URL}issues/new?{urlencode(self.BUG_TEMPLATE, encoding="utf-8")}' + log.getAttribute('value');

document.body.appendChild(link);
link.click();
document.body.removeChild(link);">
<i class="fa fa-bug"></i>Report a bug</button>"""
        )
        self.report_suggestion = ipw.HTML(
            f"""
<form target="_blank" style="width:auto;height:auto;" action="{SOURCE_URL}issues/new">
<input type="hidden" name="title" value="{self.SUGGESTION_TEMPLATE["title"]}" />
<input type="hidden" name="body" value="{self.SUGGESTION_TEMPLATE["body"]}" />
<button type="submit" class="p-Widget jupyter-widgets jupyter-button widget-button mod-{button_style.value}"
title="Create an enhancement issue on GitHub" style="width:auto;">
<i class="fa fa-star"></i>Suggest a feature/change</button></form>"""
        )
        reports = ipw.HBox(
            children=(
                ipw.HTML(
                    '<p style="font-size:14px;margin-top:0px;margin-bottom:0px">'
                    "<b>Help improve the application:</b></p>"
                ),
                self.report_bug,
                self.report_suggestion,
            ),
        )

        description = ipw.HTML(self.DESCRIPTION)

        super().__init__(
            children=(self._debug_log, logo, header, reports, description),
            layout=ipw.Layout(width="auto"),
            **kwargs,
        )

    def freeze(self):
        """Disable widget"""
        self.report_suggestion.disabled = True
        self._debug_log.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.report_suggestion.disabled = False
        self._debug_log.unfreeze()

    def reset(self):
        """Reset widget"""
        self.report_suggestion.disabled = False
        self._debug_log.reset()

    @staticmethod
    def _get_file(filename: str) -> Union[str, bytes]:
        """Read and return file"""
        path = Path(filename).resolve()
        LOGGER.debug("Trying image file path: %s", str(path))
        if path.exists() and path.is_file():
            with open(path, "rb") as file_handle:
                res = file_handle.read()
            return res

        LOGGER.debug("File %s either does not exist or is not a file", str(path))
        return ""


class OptimadeClientFAQ(ipw.Accordion):
    """A "closed" accordion with FAQ about the OPTIMADE Client"""

    FAQ = [
        {
            "Q": "Why is a given provider not shown in the client?",
            "A": """<p style="font-size:14px;">The most likely reason is that they have not yet registered with <a href="https://github.com/Materials-Consortia/providers" target="_blank">the OPTIMADE consortium's list of providers repository</a>.
Please contact the given provider and let them know they can register themselves there.</p>""",
        },
        {
            "Q": "Why is the provider I wish to use greyed out and disabled?",
            "A": """<p style="font-size:14px;">There may be different reasons:</p>
<ul style="line-height:1.5;font-size:14px;">
  <li>The provider has not supplied a link to an OPTIMADE index meta-database.</li>
  <li>The provider has implemented an unsupported specification version.</li>
  <li>The provider has supplied a link that could not be reached.</li>
  <li>The provider claims to implement a supported specification version, but certain required features are not fully implemented.</li>
</ul>
<p style="line-height:1.5;font-size:14px;">Please go to <a href="https://github.com/Materials-Consortia/providers" target="_blank">the OPTIMADE consortium's list of providers repository</a> to update the provider in question's details.</p>""",
        },
        {
            "Q": "When I choose a provider, why can I not find any databases?",
            "A": """<p style="font-size:14px;">There may be different reasons:</p>
<ul style="line-height:1.5;font-size:14px;">
  <li>The provider does not have a <code>/structures</code> endpoint.</li>
  <li>The implementation is of an unsupported version.</li>
  <li>The implementation could not be reached.</li>
</ul>
<p style="line-height:1.5;font-size:14px;">An implementation may also be removed upon the user choosing it. This is due to OPTIMADE API version incompatibility between the implementation and this client.</p>""",
        },
        {
            "Q": "I know a database hosts X number of structures, why can I only find Y?",
            "A": f"""<p style="line-height:1.5;font-size:14px;">All searches (including the raw input search) will be pre-processed prior to sending the query.
This is done to ensure the best experience when using the client.
Specifically, all structures with <code>"assemblies"</code> and <code>"unknown_positions"</code> (for pre-v1 implementations) in the <code>"structural_features"</code> property are excluded.</p>
<p style="line-height:1.5;font-size:14px;"><code>"assemblies"</code> handling will be implemented at a later time.
See <a href="{SOURCE_URL}issues/12" target="_blank">this issue</a> for more information.</p>
<p style="line-height:1.5;font-size:14px;">Finally, a provider may choose to expose only a subset of their database.</p>""",
        },
        {
            "Q": "Why are some downloadable formats greyed out and disabled for certain structures?",
            "A": """<p style="line-height:1.5;font-size:14px;">Currently, only two libraries are used to transform the OPTIMADE structure into other known data types:</p>
<ul style="line-height:1.5;font-size:14px;">
  <li>The <a href="https://github.com/Materials-Consortia/optimade-python-tools" target="_blank">OPTIMADE Python Tools</a> library.</li>
  <li>The <a href="https://wiki.fysik.dtu.dk/ase/index.html" target="_blank">Atomistic Simulation Environment (ASE)</a> library.</li>
</ul>
<p style="line-height:1.5;font-size:14px;">ASE does not support transforming structures with partial occupancies, hence the options using ASE will be disabled when such structures are chosen in the application.
There are plans to also integrate <a href="https://pymatgen.org/" target="_blank">pymatgen</a>, however, the exact integration is still under design.</p>""",
        },
    ]

    def __init__(self, **kwargs):
        faq = self._write_faq()
        super().__init__(children=(faq,), **kwargs)
        self.set_title(0, "FAQ")
        self.selected_index = None

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.selected_index = None

    def _write_faq(self) -> ipw.HTML:
        """Generate FAQ HTML"""
        value = ""
        for faq in self.FAQ:
            if value == "":
                value += f'<h4 style="font-weight:bold;">{faq["Q"]}</h4>\n{faq["A"]}'
            else:
                value += (
                    '\n\n<h4 style="font-weight:bold;margin-top:25px;">'
                    f'{faq["Q"]}</h4>\n{faq["A"]}'
                )
        return ipw.HTML(value)


class OptimadeLog(ipw.Accordion):
    """Accordion containing non-editable log output"""

    def __init__(self, **kwargs):
        self._debug = bool(os.environ.get("OPTIMADE_CLIENT_DEBUG", False))

        self.toggle_debug = ipw.Checkbox(
            value=self._debug,
            description="Show DEBUG messages",
            disabled=False,
            indent=False,
            width="auto",
            height="auto",
        )
        self.clear_cache = ipw.Button(
            description="Clear cache",
            disabled=False,
            tooltip="Clear cached responses (not logs)",
            icon="cube",
            layout={
                "visibility": "visible" if self._debug else "hidden",
                "width": "auto",
            },
        )
        self.clear_logs = ipw.Button(
            description="Clear logs",
            disabled=False,
            tooltip="Clear all log history",
            icon="edit",
            layout={
                "visibility": "visible" if self._debug else "hidden",
                "width": "auto",
            },
        )
        self.log_output = WIDGET_HANDLER.get_widget()
        super().__init__(
            children=(
                ipw.VBox(
                    children=(
                        ipw.HBox(
                            children=(
                                self.toggle_debug,
                                self.clear_cache,
                                self.clear_logs,
                            ),
                            layout={"height": "auto", "width": "auto"},
                        ),
                        self.log_output,
                    )
                ),
            ),
            **kwargs,
        )
        self.set_title(0, "Log")
        self.selected_index = 0 if self._debug else None

        self.toggle_debug.observe(self._toggle_debug_logging, names="value")
        self.clear_cache.on_click(self._clear_cache)
        self.clear_logs.on_click(self._clear_logs)

    def freeze(self):
        """Disable widget"""
        self.toggle_debug.disabled = True
        self.log_output.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.toggle_debug.disabled = False
        self.log_output.unfreeze()

    def reset(self):
        """Reset widget"""
        self.selected_index = None
        self.toggle_debug.value = self._debug
        self.toggle_debug.disabled = False
        self.log_output.reset()

    def _toggle_debug_logging(self, change: dict):
        """Set logging level depending on toggle button"""
        if change["new"]:
            # Set logging level DEBUG
            WIDGET_HANDLER.setLevel(logging.DEBUG)
            LOGGER.info("Set log output in widget to level DEBUG")
            LOGGER.debug("This should now be shown")

            # Show debug buttons
            self.clear_cache.layout.visibility = "visible"
            self.clear_logs.layout.visibility = "visible"
        else:
            # Set logging level to INFO
            WIDGET_HANDLER.setLevel(logging.INFO)
            LOGGER.info("Set log output in widget to level INFO")
            LOGGER.debug("This should now NOT be shown")

            # Hide debug buttons
            self.clear_cache.layout.visibility = "hidden"
            self.clear_logs.layout.visibility = "hidden"

    @staticmethod
    def _clear_cache(_):
        """Clear cached responses (not logs)"""
        if str(LOG_DIR).startswith(str(CACHE_DIR)):
            log_sub_dir = list(Path(str(LOG_DIR)[len(f"{CACHE_DIR}/") :]).parts)

        LOGGER.debug(
            "Cache dir: %s - Log dir: %s - Log sub dir parts: %s",
            CACHE_DIR,
            LOG_DIR,
            log_sub_dir,
        )

        for dirpath, dirnames, filenames in os.walk(CACHE_DIR):
            log_dir_part = log_sub_dir.pop(0) if log_sub_dir else ""
            if not log_sub_dir:
                LOGGER.debug(
                    "No more log sub directory parts. Removing %r from dirnames list.",
                    log_dir_part,
                )
                dirnames.remove(log_dir_part)

            for directory in list(dirnames):
                if directory == log_dir_part:
                    continue
                LOGGER.debug(
                    "Removing folder: %s", Path(dirpath).joinpath(directory).resolve()
                )
                shutil.rmtree(
                    Path(dirpath).joinpath(directory).resolve(), ignore_errors=True
                )
                dirnames.remove(directory)
            for filename in filenames:
                LOGGER.debug(
                    "Removing file: %s", Path(dirpath).joinpath(filename).resolve()
                )
                os.remove(Path(dirpath).joinpath(filename).resolve())
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _clear_logs(_):
        """Clear all logs"""
        shutil.rmtree(LOG_DIR, ignore_errors=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
