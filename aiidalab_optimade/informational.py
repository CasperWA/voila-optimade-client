from pathlib import Path
from typing import Union

import ipywidgets as ipw

from aiidalab_optimade.utils import LOGGER, __optimade_version__


IMG_DIR = Path(__file__).parent.parent.joinpath("img")


class HeaderDescription(ipw.VBox):
    """Top logo and description of the OPTIMADE Client"""

    DESCRIPTION = f"""<p style="font-size:14px;"><b>Currently valid OPTIMADE API version</b>: <code>v{__optimade_version__}</code></p>
<p style="font-size:14px;"><b>Source code</b>: <a href="https://github.com/aiidalab/aiidalab-optimade/" target="_blank">GitHub</a></p>
<p style="font-size:14px;"><a href="https://github.com/aiidalab/aiidalab-optimade/issues/new" target="_blank">
<b>Click here to report an issue and help improve the application!</b>
</a></p>
<p style="line-height:1.5;font-size:14px;">
This is a friendly client to search through databases and other implementations exposing an OPTIMADE RESTful API.
To get more information about the OPTIMADE API,
please see <a href="https://www.optimade.org/" target="_blank">the offical web page</a>.
All providers are retrieved from <a href="https://providers.optimade.org/" target="_blank">Materials-Consortia's list of providers</a>.
</p>
<p style="line-height:1.5;font-size:14px;margin-top:5px;">
<i>Note</i>: The structure property <code>assemblies</code> is currently not supported.
Follow <a href="https://github.com/aiidalab/aiidalab-optimade/issues/12" target="_blank">the issue on GitHub</a> to learn more.
</p>
"""

    def __init__(self, logo: str = None, **kwargs):
        logo = logo if logo is not None else "optimade-text-right-transparent-bg.png"
        logo = self._get_file(str(IMG_DIR.joinpath(logo)))
        logo = ipw.Image(value=logo, format="png", width=375, height=137.5)

        description = ipw.HTML(self.DESCRIPTION)

        super().__init__(
            children=(logo, description), layout=ipw.Layout(width="auto"), **kwargs
        )

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""

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
            "Q": "Why is a provider from Materials-Consortia's list of providers not shown in the "
            "client?",
            "A": """<p style="font-size:14px;">There may be different reasons:</p>
<ul style="line-height:1.5;font-size:14px;">
  <li>The provider has not supplied a link to an OPTIMADE index meta-database</li>
  <li>The provider has implemented an unsupported version</li>
  <li>The provider has supplied a link that could not be reached</li>
</ul>
<p style="line-height:1.5;font-size:14px;">
Please go to <a href="https://github.com/Materials-Consortia/providers" target="_blank">the Materials-Consortia list of providers repository</a> to update the provider in question's details.
</p>""",
        },
        {
            "Q": "When I choose a provider, why can I not find any databases?",
            "A": """<p style="font-size:14px;">There may be different reasons:</p>
<ul style="line-height:1.5;font-size:14px;">
  <li>The provider does not have a <code>/structures</code> endpoint</li>
  <li>The implementation is of an unsupported version</li>
  <li>The implementation could not be reached</li>
</ul>
<p style="line-height:1.5;font-size:14px;">
An implementation may also be removed upon choosing it. This is do to OPTIMADE API version incompatibility between the implementation and this client.
</p>""",
        },
        {
            "Q": "I know a database hosts X number of structures, why can I only find Y?",
            "A": """<p style="line-height:1.5;font-size:14px;">
All searches (including the raw input search) will be pre-processed prior to sending the query.
This is done to ensure the best experience when using the client.
Specifically, all structures with <code>"assemblies"</code> and <code>"unknown_positions"</code>
in the <code>"structural_features"</code> property are excluded.
</p>
<p style="line-height:1.5;font-size:14px;">
<code>"assemblies"</code> handling will be implemented at a later time.
See <a href="https://github.com/aiidalab/aiidalab-optimade/issues/12" target="_blank">this issue</a> for more information.
</p>
<p style="line-height:1.5;font-size:14px;">
<code>"unknown_positions"</code> may be handled later, however, since these structures present difficulties for viewing, it will not be prioritized.
</p>
<p style="line-height:1.5;font-size:14px;">
Finally, a provider may choose to expose only a subset of their database.
</p>""",
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
                value += f'\n\n<h4 style="font-weight:bold;margin-top:25px;">{faq["Q"]}</h4>\n{faq["A"]}'
        return ipw.HTML(value)


# faq = ipw.HTML(
#     value= \
# """<h4 style="font-weight:bold;">Why is a provider from Materials-Consortia's list of providers not shown in the client?</h4>
# <p style="font-size:14px;">There may be different reasons:</p>
# <ul style="line-height:1.5;font-size:14px;">
#   <li>The provider has not supplied a link to an OPTIMADE index meta-database</li>
#   <li>The provider has implemented an unsupported version</li>
#   <li>The provider has supplied a link that could not be reached</li>
# </ul>
# <p style="line-height:1.5;font-size:14px;">Please go to <a href="https://github.com/Materials-Consortia/providers" target="_blank">the Materials-Consortia list of providers repository</a> to update the provider in question's details.</p>

# <h4 style="font-weight:bold;margin-top:25px;">When I choose a provider, why can I not find any databases?</h4>
# <p style="font-size:14px;">There may be different reasons:</p>
# <ul style="line-height:1.5;font-size:14px;">
#   <li>The provider does not have a <code>/structures</code> endpoint</li>
#   <li>The implementation is of an unsupported version</li>
#   <li>The implementation could not be reached</li>
# </ul>
# <p style="line-height:1.5;font-size:14px;">An implementation may also be removed upon choosing it. This is do to OPTIMADE API version incompatibility between the implementation and this client.</p>

# <h4 style="font-weight:bold;margin-top:25px;">I know a database hosts X number of structures, why can I only find Y?</h4>
# <p style="line-height:1.5;font-size:14px;">
# All searches (including the raw input search) will be pre-processed prior to sending the query.
# This is done to ensure the best experience when using the client.
# Specifically, all structures with <code>"assemblies"</code> and <code>"unknown_positions"</code>
# in the <code>"structural_features"</code> property are excluded.
# </p>
# <p style="line-height:1.5;font-size:14px;">
# <code>"assemblies"</code> handling will be implemented at a later time.
# See <a href="https://github.com/aiidalab/aiidalab-optimade/issues/12" target="_blank">this issue</a> for more information.
# </p>
# <p style="line-height:1.5;font-size:14px;">
# <code>"unknown_positions"</code> may be handled later, however, since these structures present difficulties for viewing, it will not be prioritized.
# </p>
# <p style="line-height:1.5;font-size:14px;">
# Finally, a provider may choose to expose only a subset of their database.
# </p>
# """
# )
