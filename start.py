import ipywidgets as ipw


def get_start_widget(appbase, jupbase, notebase):
    return ipw.HTML(
        f"""
        <table>
        <tr>
        <th style="text-align:center">Preferences</th>
        <tr>
        <td valign="top"><ul>
            <li><a href="{appbase}/plugin_list.ipynb" target="_blank">Plugins</a></li>
        </ul></td>
        </tr>
        </table>
    <div align="center">
        <a href="{appbase}/qe.ipynb" target="_blank">
            <img src="https://gitlab.com/QEF/q-e/raw/develop/logo.jpg" height="120px" width=243px">
        </a>
    </div>"""
    )
