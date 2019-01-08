import ipywidgets as ipw

template = """
<table>
<tr>
  <td valign="top"><ul>
    <li><a href="{appbase}/optimade.ipynb" target="_blank">Use OPTiMaDe to load a structure</a></li>
  </ul></td>
</tr>
</table>
"""

def get_start_widget(appbase, jupbase, notebase):
    html = template.format(appbase=appbase, jupbase=jupbase, notebase=notebase)
    return ipw.HTML(html)
    
#EOF
