TEMPLATE = """
<p>Use OPTIMADE to find a structure in common materials databases</p>
<div align="center">
  <a href="{appbase}/OPTIMADE_general.ipynb" target="_blank">
    <img src="{appbase}/img/optimade-text-right-transparent-bg.png" alt="OPTIMADE: Open Databases Integration for Materials Design">
  </a>
</div>
"""


def get_start_widget(appbase, jupbase, notebase):
    """Create content for Home App"""
    from ipywidgets import HTML

    html = TEMPLATE.format(appbase=appbase, jupbase=jupbase, notebase=notebase)
    return HTML(html)


# EOF
