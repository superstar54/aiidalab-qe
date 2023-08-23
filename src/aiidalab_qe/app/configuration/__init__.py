# -*- coding: utf-8 -*-
"""Widgets for the submission of bands work chains.

Authors: AiiDAlab team
"""
from __future__ import annotations

import ipywidgets as ipw
import traitlets as tl
from aiida import orm
from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiidalab_widgets_base import WizardAppWidgetStep

from aiidalab_qe.app.parameters import DEFAULT_PARAMETERS

from .advanced import AdvancedSettings
from .pseudos import PseudoFamilySelector, PseudoSetter
from .workflow import WorkChainSettings


class ConfigureQeAppWorkChainStep(ipw.VBox, WizardAppWidgetStep):
    confirmed = tl.Bool()
    previous_step_state = tl.UseEnum(WizardAppWidgetStep.State)
    workchain_settings = tl.Instance(WorkChainSettings, allow_none=True)
    pseudo_family_selector = tl.Instance(PseudoFamilySelector, allow_none=True)
    pseudo_setter = tl.Instance(PseudoSetter, allow_none=True)
    advanced_settings = tl.Instance(AdvancedSettings, allow_none=True)
    input_structure = tl.Instance(orm.StructureData, allow_none=True)

    def __init__(self, **kwargs):
        self.workchain_settings = WorkChainSettings()
        self.workchain_settings.relax_type.observe(self._update_state, "value")
        self.workchain_settings.bands_run.observe(self._update_state, "value")
        self.workchain_settings.pdos_run.observe(self._update_state, "value")

        self.pseudo_family_selector = PseudoFamilySelector()
        self.pseudo_setter = PseudoSetter()
        ipw.dlink(
            (self.pseudo_family_selector, "value"),
            (self.pseudo_setter, "pseudo_family"),
        )

        self.advanced_settings = AdvancedSettings()

        ipw.dlink(
            (self.workchain_settings.workchain_protocol, "value"),
            (self.advanced_settings.kpoints, "kpoints_distance_default"),
            lambda protocol: PwBaseWorkChain.get_protocol_inputs(protocol)[
                "kpoints_distance"
            ],
        )

        ipw.dlink(
            (self.workchain_settings.workchain_protocol, "value"),
            (self.advanced_settings.smearing, "degauss_default"),
            lambda protocol: PwBaseWorkChain.get_protocol_inputs(protocol)["pw"][
                "parameters"
            ]["SYSTEM"]["degauss"],
        )

        ipw.dlink(
            (self.workchain_settings.workchain_protocol, "value"),
            (self.advanced_settings.smearing, "smearing_default"),
            lambda protocol: PwBaseWorkChain.get_protocol_inputs(protocol)["pw"][
                "parameters"
            ]["SYSTEM"]["smearing"],
        )

        self.tab = ipw.Tab(
            children=[
                self.workchain_settings,
                ipw.VBox(
                    children=[
                        self.advanced_settings,
                        self.pseudo_family_selector,
                        self.pseudo_setter,
                    ]
                ),
            ],
            layout=ipw.Layout(min_height="250px"),
        )

        self.tab.set_title(0, "Workflow")
        self.tab.set_title(1, "Advanced settings")

        self._submission_blocker_messages = ipw.HTML()

        self.confirm_button = ipw.Button(
            description="Confirm",
            tooltip="Confirm the currently selected settings and go to the next step.",
            button_style="success",
            icon="check-circle",
            disabled=True,
            layout=ipw.Layout(width="auto"),
        )

        self.confirm_button.on_click(self.confirm)

        super().__init__(
            children=[
                self.tab,
                self._submission_blocker_messages,
                self.confirm_button,
            ],
            **kwargs,
        )

    @tl.observe("input_structure")
    def _update_input_structure(self, change):
        if self.input_structure is not None:
            self.advanced_settings.magnetization._update_widget(change)
            self.pseudo_setter.structure = change["new"]

    @tl.observe("previous_step_state")
    def _observe_previous_step_state(self, change):
        self._update_state()

    def set_input_parameters(self, parameters):
        """Set the inputs in the GUI based on a set of parameters."""

        with self.hold_trait_notifications():
            # Work chain settings
            self.workchain_settings.relax_type.value = parameters["relax_type"]
            self.workchain_settings.spin_type.value = parameters["spin_type"]
            self.workchain_settings.electronic_type.value = parameters[
                "electronic_type"
            ]
            self.workchain_settings.bands_run.value = parameters["run_bands"]
            self.workchain_settings.pdos_run.value = parameters["run_pdos"]
            self.workchain_settings.workchain_protocol.value = parameters["protocol"]

            # Advanced settings
            self.pseudo_family_selector.value = parameters["pseudo_family"]
            if parameters.get("kpoints_distance_override", None) is not None:
                self.advanced_settings.kpoints.distance.value = parameters[
                    "kpoints_distance_override"
                ]
                self.advanced_settings.kpoints.override.value = True
            if parameters.get("degauss_override", None) is not None:
                self.advanced_settings.smearing.degauss.value = parameters[
                    "degauss_override"
                ]
                self.advanced_settings.smearing.override.value = True
            if parameters.get("smearing_override", None) is not None:
                self.advanced_settings.smearing.smearing.value = parameters[
                    "smearing_override"
                ]
                self.advanced_settings.smearing.override.value = True

    def _update_state(self, _=None):
        if self.previous_step_state == self.State.SUCCESS:
            self.confirm_button.disabled = False
            self._submission_blocker_messages.value = ""
            self.state = self.State.CONFIGURED
        elif self.previous_step_state == self.State.FAIL:
            self.state = self.State.FAIL
        else:
            self.confirm_button.disabled = True
            self.state = self.State.INIT
            self.set_input_parameters(DEFAULT_PARAMETERS)

    def confirm(self, _=None):
        self.confirm_button.disabled = False
        self.state = self.State.SUCCESS

    @tl.default("state")
    def _default_state(self):
        return self.State.INIT

    def reset(self):
        with self.hold_trait_notifications():
            self.set_input_parameters(DEFAULT_PARAMETERS)