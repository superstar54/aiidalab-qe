# from aiidalab_qe.bands.result import Result
from aiidalab_qe.app.common.panel import OutlinePanel

from .result import Result
from .setting import Setting
from .workchain import workchain_and_builder


class XpsOutline(OutlinePanel):
    title = "XPS"
    help = """"""


property = {
    "outline": XpsOutline,
    "setting": Setting,
    "result": Result,
    "workchain": workchain_and_builder,
}
