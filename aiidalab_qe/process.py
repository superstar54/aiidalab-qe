"""Widgets related to process management."""
from dataclasses import dataclass
from threading import Event, Lock, Thread

import ipywidgets as ipw
import traitlets


def get_ctime(time_str):
    """"""
    from datetime import datetime, timezone

    time_obj = datetime.fromisoformat(time_str)
    time_diff = datetime.now(timezone.utc) - time_obj
    total_seconds = int(time_diff.total_seconds())
    # Determine the largest unit
    if total_seconds >= 60 * 60 * 24:
        unit = "d"
        val = total_seconds // (60 * 60 * 24)
    elif total_seconds >= 60 * 60:
        unit = "h"
        val = total_seconds // (60 * 60)
    elif total_seconds >= 60:
        unit = "min"
        val = total_seconds // 60
    else:
        unit = "s"
        val = total_seconds

    # Display the largest unit and value
    return f"{val} {unit}"


class WorkChainSelector(ipw.HBox):

    # The PK of a 'aiida.workflows:quantumespresso.pw.bands' WorkChainNode.
    value = traitlets.Int(allow_none=True)

    # When this trait is set to a positive value, the work chains are automatically
    # refreshed every `auto_refresh_interval` seconds.
    auto_refresh_interval = traitlets.Int()  # seconds

    # Indicate whether the widget is currently updating the work chain options.
    busy = traitlets.Bool(read_only=True)

    # Note: We use this class as a singleton to reset the work chains selector
    # widget to its default stage (no work chain selected), because we cannot
    # use `None` as setting the widget's value to None will lead to "no selection".
    _NO_PROCESS = object()

    FMT_WORKCHAIN = "{wc.pk:6}{wc.ctime:>10}\t{wc.state:<16}\t{wc.formula} \t {wc.relax_info} \t {wc.properties_info}"

    def __init__(self, **kwargs):
        self.work_chains_prompt = ipw.HTML(
            "<b>Select computed workflow or start a new one:</b>&nbsp;"
        )
        self.work_chains_selector = ipw.Dropdown(
            options=[("New workflow...", self._NO_PROCESS)],
            layout=ipw.Layout(min_width="300px", flex="1 1 auto"),
        )
        ipw.dlink(
            (self.work_chains_selector, "value"),
            (self, "value"),
            transform=lambda pk: None if pk is self._NO_PROCESS else pk,
        )

        self.refresh_work_chains_button = ipw.Button(description="Refresh")
        self.refresh_work_chains_button.on_click(self.refresh_work_chains)

        self._refresh_lock = Lock()
        self._refresh_thread = None
        self._stop_refresh_thread = Event()
        self._update_auto_refresh_thread_state()

        super().__init__(
            children=[
                self.work_chains_prompt,
                self.work_chains_selector,
                self.refresh_work_chains_button,
            ],
            **kwargs,
        )

    @dataclass
    class WorkChainData:
        pk: int
        ctime: str
        state: str
        formula: str
        relax_info: str
        properties_info: str

    @classmethod
    def find_work_chains(cls):
        from aiidalab_restapi.api import restapi_get_node_by_filter

        # TODO add extra info: relax, bands, pdos
        # I donn't know it not show all of the result, so I add a time here, will be removed later.
        results = restapi_get_node_by_filter(
            "process_type ILIKE '%aiidalab_qe_workchain%'  & mtime >= 2023-03-01"
        )
        results.reverse()

        for data in results:
            formula = data["incoming"]["rows"][0]["node"]["extras"]["formula"]
            state = data["attributes"].get("process_state", "except")

            ctime = get_ctime(data["ctime"])

            yield cls.WorkChainData(
                formula=formula,
                relax_info="relax: none",
                properties_info="properties: none",
                pk=data["id"],
                ctime=ctime,
                state=state,
            )

    @traitlets.default("busy")
    def _default_busy(self):
        return True

    @traitlets.observe("busy")
    def _observe_busy(self, change):
        for child in self.children:
            child.disabled = change["new"]

    def refresh_work_chains(self, _=None):
        with self._refresh_lock:
            try:
                self.set_trait("busy", True)  # disables the widget

                with self.hold_trait_notifications():
                    # We need to restore the original value, because it may be reset due to this issue:
                    # https://github.com/jupyter-widgets/ipywidgets/issues/2230
                    original_value = self.work_chains_selector.value

                    self.work_chains_selector.options = [
                        ("New workflow...", self._NO_PROCESS)
                    ] + [
                        (self.FMT_WORKCHAIN.format(wc=wc), wc.pk)
                        for wc in self.find_work_chains()
                    ]

                    self.work_chains_selector.value = original_value
            finally:
                self.set_trait("busy", False)  # reenable the widget

    def _auto_refresh_loop(self):
        while True:
            self.refresh_work_chains()
            if self._stop_refresh_thread.wait(timeout=self.auto_refresh_interval):
                break

    def _update_auto_refresh_thread_state(self):
        if self.auto_refresh_interval > 0 and self._refresh_thread is None:
            # start thread
            self._stop_refresh_thread.clear()
            self._refresh_thread = Thread(target=self._auto_refresh_loop)
            self._refresh_thread.start()

        elif self.auto_refresh_interval <= 0 and self._refresh_thread is not None:
            # stop thread
            self._stop_refresh_thread.set()
            self._refresh_thread.join(timeout=30)
            self._refresh_thread = None

    @traitlets.default("auto_refresh_interval")
    def _default_auto_refresh_interval(self):
        return 10  # seconds

    @traitlets.observe("auto_refresh_interval")
    def _observe_auto_refresh_interval(self, change):
        if change["new"] != change["old"]:
            self._update_auto_refresh_thread_state()

    @traitlets.observe("value")
    def _observe_value(self, change):
        if change["old"] == change["new"]:
            return

        new = self._NO_PROCESS if change["new"] is None else change["new"]

        if new not in {pk for _, pk in self.work_chains_selector.options}:
            self.refresh_work_chains()

        self.work_chains_selector.value = new
