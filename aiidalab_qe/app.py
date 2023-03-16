import ipywidgets as ipw
from aiida.orm import load_node
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
from aiidalab_widgets_base.bug_report import (
    install_create_github_issue_exception_handler,
)
from importlib_resources import files
from jinja2 import Environment

from aiidalab_qe import static
from aiidalab_qe.process import WorkChainSelector
from aiidalab_qe.steps import (
    ConfigureQeAppWorkChainStep,
    SubmitQeAppWorkChainStep,
    ViewQeAppWorkChainStatusAndResultsStep,
)
from aiidalab_qe.structures import Examples, StructureSelectionStep
from aiidalab_qe.version import __version__

OptimadeQueryWidget.title = "OPTIMADE"  # monkeypatch
env = Environment()

template = files(static).joinpath("welcome.jinja").read_text()
style = files(static).joinpath("style.css").read_text()
welcome_message = ipw.HTML(env.from_string(template).render(style=style))
footer = ipw.HTML(
    f'<p style="text-align:right;">Copyright (c) 2022 AiiDAlab team (EPFL)&#8195Version: {__version__}</p>'
)


class QEApp:
    def __init__(self) -> None:
        pass

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
            if change["old"] == change["new"]:
                return
            pk = change["new"]
            if pk is None:
                self.steps.reset()
                self.steps.selected_index = 0
            else:
                process = load_node(pk)
                with structure_manager_widget.hold_sync():
                    with structure_selection_step.hold_sync():
                        self.steps.selected_index = 3
                        structure_manager_widget.input_structure = (
                            process.inputs.structure
                        )
                        structure_selection_step.structure = process.inputs.structure
                        structure_selection_step.confirmed_structure = (
                            process.inputs.structure
                        )
                        configure_qe_app_work_chain_step.state = (
                            WizardAppWidgetStep.State.SUCCESS
                        )
                        submit_qe_app_work_chain_step.process = process

        self.work_chain_selector.observe(_observe_process_selection, "value")
        ipw.dlink(
            (submit_qe_app_work_chain_step, "process"),
            (self.work_chain_selector, "value"),
            transform=lambda node: None if node is None else node,
        )

    def display(self):
        from IPython import display

        app_with_work_chain_selector = ipw.VBox(
            children=[self.work_chain_selector, self.steps]
        )
        output = ipw.Output()
        install_create_github_issue_exception_handler(
            output,
            url="https://github.com/aiidalab/aiidalab-qe/issues/new",
            labels=("bug", "automated-report"),
        )

        with output:
            display(welcome_message, app_with_work_chain_selector, footer)

        display(output)
