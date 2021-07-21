TEMPLATE = """
<div align="center">
  <a href="{appbase}/OPTIMADE Client.ipynb" target="_blank" title="OPTIMADE Client">
    <img src="{appbase}/img/optimade-text-right-transparent-bg.png" alt="OPTIMADE: Open Databases Integration for Materials Design" width="375px" height="137.5px">
  </a>
</div>
"""


def get_start_widget(appbase, jupbase, notebase):
    """Create content for Home App"""
    from ipywidgets import HTML

    html = TEMPLATE.format(appbase=appbase, jupbase=jupbase, notebase=notebase)
    return HTML(html)
