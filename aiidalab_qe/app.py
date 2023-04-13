import ipywidgets as ipw
from aiidalab_widgets_base import (
    BasicCellEditor,
    BasicStructureEditor,
    OptimadeQueryWidget,
    StructureBrowserWidget,
    StructureExamplesWidget,
    StructureManagerWidget,
    StructureUploadWidget,
    WizardAppWidget,
    WizardAppWidgetStep,
)

from aiidalab_qe.process import WorkChainSelector
from aiidalab_qe.steps import (
    ConfigureQeAppWorkChainStep,
    SubmitQeAppWorkChainStep,
    ViewQeAppWorkChainStatusAndResultsStep,
)
from aiidalab_qe.structures import Examples, StructureSelectionStep

OptimadeQueryWidget.title = "OPTIMADE"  # monkeypatch


class QEApp:
    def __init__(self) -> None:
        # Create the application steps
        structure_manager_widget = StructureManagerWidget(
            importers=[
                StructureUploadWidget(title="Upload file"),
                OptimadeQueryWidget(embedded=False),
                StructureBrowserWidget(title="AiiDA database"),
                StructureExamplesWidget(title="From Examples", examples=Examples),
            ],
            editors=[
                BasicCellEditor(title="Edit cell"),
                BasicStructureEditor(title="Edit structure"),
            ],
            node_class="StructureData",
            storable=False,
            configuration_tabs=["Cell", "Selection", "Appearance", "Download"],
        )
        structure_selection_step = StructureSelectionStep(
            manager=structure_manager_widget, auto_advance=True
        )
        configure_qe_app_work_chain_step = ConfigureQeAppWorkChainStep(
            auto_advance=True
        )
        submit_qe_app_work_chain_step = SubmitQeAppWorkChainStep(auto_advance=True)
        view_qe_app_work_chain_status_and_results_step = (
            ViewQeAppWorkChainStatusAndResultsStep()
        )

        # Link the application steps
        ipw.dlink(
            (structure_selection_step, "state"),
            (configure_qe_app_work_chain_step, "previous_step_state"),
        )
        ipw.dlink(
            (structure_selection_step, "confirmed_structure"),
            (submit_qe_app_work_chain_step, "input_structure"),
        )
        ipw.dlink(
            (configure_qe_app_work_chain_step, "state"),
            (submit_qe_app_work_chain_step, "previous_step_state"),
        )
        ipw.dlink(
            (configure_qe_app_work_chain_step, "workchain_settings"),
            (submit_qe_app_work_chain_step, "workchain_settings"),
        )
        ipw.dlink(
            (configure_qe_app_work_chain_step, "kpoints_settings"),
            (submit_qe_app_work_chain_step, "kpoints_settings"),
        )
        ipw.dlink(
            (configure_qe_app_work_chain_step, "smearing_settings"),
            (submit_qe_app_work_chain_step, "smearing_settings"),
        )
        ipw.dlink(
            (configure_qe_app_work_chain_step, "pseudo_family_selector"),
            (submit_qe_app_work_chain_step, "pseudo_family_selector"),
        )

        ipw.dlink(
            (submit_qe_app_work_chain_step, "process"),
            (view_qe_app_work_chain_status_and_results_step, "process"),
            transform=lambda node: node if node is not None else None,
        )

        # Add the application steps to the application
        self.steps = WizardAppWidget(
            steps=[
                ("Select structure", structure_selection_step),
                ("Configure workflow", configure_qe_app_work_chain_step),
                ("Choose computational resources", submit_qe_app_work_chain_step),
                ("Status & Results", view_qe_app_work_chain_status_and_results_step),
            ]
        )

        # Reset all subsequent steps in case that a new structure is selected
        def _observe_structure_selection(change):
            with structure_selection_step.hold_sync():
                if (
                    structure_selection_step.confirmed_structure is not None
                    and structure_selection_step.confirmed_structure != change["new"]
                ):
                    self.steps.reset()

        structure_selection_step.observe(_observe_structure_selection, "structure")

        # Add process selection header
        self.work_chain_selector = WorkChainSelector(layout=ipw.Layout(width="auto"))

        def _observe_process_selection(change):
            from aiidalab_restapi.api import restapi_get_inputs_by_pk
            from aiidalab_restapi.utils import create_structure

            if change["old"] == change["new"]:
                return
            pk = change["new"]
            if pk is None:
                self.steps.reset()
                self.steps.selected_index = 0
            else:
                inputs = restapi_get_inputs_by_pk(pk)
                structure = create_structure(inputs["structure"])
                with structure_manager_widget.hold_sync():
                    with structure_selection_step.hold_sync():
                        self.steps.selected_index = 3
                        structure_manager_widget.input_structure = structure
                        structure_selection_step.structure = structure
                        structure_selection_step.confirmed_structure = structure
                        configure_qe_app_work_chain_step.state = (
                            WizardAppWidgetStep.State.SUCCESS
                        )
                        submit_qe_app_work_chain_step.process = pk

        self.work_chain_selector.observe(_observe_process_selection, "value")
        ipw.dlink(
            (submit_qe_app_work_chain_step, "process"),
            (self.work_chain_selector, "value"),
            transform=lambda node: None if node is None else node,
        )
        self.work_chain = ipw.VBox(children=[self.work_chain_selector, self.steps])
