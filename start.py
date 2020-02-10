import ipywidgets as ipw

TEMPLATE = """
<table>
<tr>
  <td valign="top"><ul>
    <li><a href="{appbase}/old_optimade.ipynb" target="_blank">(Depracated) Use OPTiMaDe to load a structure</a></li>
    <li><a href="{appbase}/OPTiMaDe general.ipynb" target="_blank">Use OPTiMaDe to find a structure</a></li>
    <li><a href="{appbase}/optimade.ipynb" target="_blank">Check out central OPTiMaDe search-and-find structure widget</a></li>
  </ul></td>
</tr>
</table>
"""


def get_start_widget(appbase, jupbase, notebase):
    """Create content for Home App"""
    html = TEMPLATE.format(appbase=appbase, jupbase=jupbase, notebase=notebase)
    return ipw.HTML(html)


# EOF
