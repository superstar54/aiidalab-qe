# AiiDA imports.
from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import ToContext, WorkChain, if_
from aiida.plugins import DataFactory

# AiiDA Quantum ESPRESSO plugin inputs.
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_quantumespresso.workflows.pw.relax import PwRelaxWorkChain

StructureData = DataFactory("core.structure")

# I removed the `validate_properties`, because the `properties` to be
# calculated are not fixed anymore. It depends on the installed plugins.

# load entry points
def get_entries(entry_point_name="aiidalab_qe.configuration"):
    from importlib.metadata import entry_points

    entries = {}
    for entry_point in entry_points().get(entry_point_name, []):
        entries[entry_point.name] = entry_point.load()

    return entries


def get_entry_items(entry_point_name, item_name="outline"):
    entries = get_entries(entry_point_name)
    return {
        name: entry_point.get(item_name)
        for name, entry_point in entries.items()
        if entry_point.get(item_name, False)
    }


entries = get_entry_items("aiidalab_qe.property", "workchain")

class QeAppWorkChain(WorkChain):
    """WorkChain designed to calculate the requested properties in the AiiDAlab Quantum ESPRESSO app."""

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)
        spec.input('structure', valid_type=StructureData,
                   help='The inputs structure.')
        spec.input('clean_workdir', valid_type=orm.Bool, default=lambda: orm.Bool(False),
                   help='If `True`, work directories of all called calculation will be cleaned at the end of execution.')
        spec.expose_inputs(PwRelaxWorkChain, namespace='relax', exclude=('clean_workdir', 'structure', 'base_final_scf'),
                           namespace_options={'required': False, 'populate_defaults': False,
                                              'help': 'Inputs for the `PwRelaxWorkChain`, if not specified at all, the relaxation step is skipped.'})
        spec.expose_outputs(PwRelaxWorkChain, namespace='relax')
        for name, entry_point in entries.items():
            plugin_workchain = entry_point["workchain"]
            spec.expose_inputs(
                plugin_workchain,
                namespace=name,
                exclude=entry_point["exclude"],
                namespace_options={
                    "required": False,
                    "populate_defaults": False,
                    "help": f"Inputs for the {name} plugin.",
                },
            )
            spec.expose_outputs(plugin_workchain, namespace=name)
            spec.exit_code(
                404 + 1,
                f"ERROR_SUB_PROCESS_FAILED_{name}",
                message=f"The plugin {name} WorkChain sub process failed",
            )
        spec.outline(
            cls.setup,
            if_(cls.should_run_relax)(
                cls.run_relax,
                cls.inspect_relax
            ),
            cls.run_plugin,
            cls.inspect_plugin,
            cls.results
        )
        spec.exit_code(401, 'ERROR_SUB_PROCESS_FAILED_RELAX',
                       message='The PwRelaxWorkChain sub process failed')

        # yapf: enable

    @classmethod
    def get_builder_from_protocol(cls, structure, parameters):
        """Return a builder prepopulated with inputs selected according to the chosen protocol."""
        from aiidalab_qe.app.plugins.relax.workchain import (
            get_builder as get_relax_builder,
        )

        builder = cls.get_builder()
        # Set the structure.
        builder.structure = structure
        protocol = parameters["basic"].pop("protocol", "moderate")
        codes = parameters.pop("codes", {})
        #
        # relax workchain
        if parameters["workflow"]["relax_type"] == "none":
            parameters["workflow"]["properties"]["relax"] = False
            builder.pop("relax", None)
        else:
            parameters["workflow"]["properties"]["relax"] = True
            relax_builder = get_relax_builder(codes, structure, parameters)
            builder.relax = relax_builder

        # add plugin workchain
        for name, entry_point in entries.items():
            if parameters["workflow"]["properties"][name]:
                plugin_builder = entry_point["get_builder"](codes, structure, parameters)
                setattr(builder, name, plugin_builder)
            else:
                builder.pop(name, None)
        # TODO check if we need to clean the workdir
        # builder.clean_workdir = orm.Bool(clean_workdir)

        return builder

    def setup(self):
        """Perform the initial setup of the work chain, setup the input structure
        and the logic to determine which sub workchains to run.
        """
        self.ctx.plugin_entries = entries
        self.ctx.current_structure = self.inputs.structure
        self.ctx.current_number_of_bands = None
        self.ctx.scf_parent_folder = None

    def should_run_relax(self):
        """Check if the geometry of the input structure should be optimized."""
        return "relax" in self.inputs

    def run_relax(self):
        """Run the `PwRelaxWorkChain`."""
        inputs = AttributeDict(self.exposed_inputs(PwRelaxWorkChain, namespace="relax"))
        inputs.metadata.call_link_label = "relax"
        inputs.structure = self.ctx.current_structure

        inputs = prepare_process_inputs(PwRelaxWorkChain, inputs)
        running = self.submit(PwRelaxWorkChain, **inputs)

        self.report(f"launching PwRelaxWorkChain<{running.pk}>")

        return ToContext(workchain_relax=running)

    def inspect_relax(self):
        """Verify that the `PwRelaxWorkChain` finished successfully."""
        workchain = self.ctx.workchain_relax

        if not workchain.is_finished_ok:
            self.report(
                f"PwRelaxWorkChain failed with exit status {workchain.exit_status}"
            )
            return self.exit_codes.ERROR_SUB_PROCESS_FAILED_RELAX
        else:
            # Attach the output nodes directly as outputs of the workchain.
            self.out_many(
                self.exposed_outputs(
                    self.ctx.workchain_relax, PwRelaxWorkChain, namespace="relax"
                )
            )

        if "output_structure" in workchain.outputs:
            self.ctx.current_structure = workchain.outputs.output_structure
            self.ctx.current_number_of_bands = (
                workchain.outputs.output_parameters.get_attribute("number_of_bands")
            )

    def should_run_plugin(self, name):
        return name in self.inputs

    def run_plugin(self):
        """Run the plugin `WorkChain`."""
        plugin_running = {}
        self.report(f"Plugins: {entries}")
        for name, entry_point in entries.items():
            if not self.should_run_plugin(name):
                continue
            self.report(f"Run plugin : {name}")
            plugin_workchain = entry_point["workchain"]
            inputs = AttributeDict(
                self.exposed_inputs(plugin_workchain, namespace=name)
            )
            inputs.metadata.call_link_label = name
            inputs.structure = self.ctx.current_structure
            inputs = prepare_process_inputs(plugin_workchain, inputs)
            self.report(f"plugin inputs: {inputs}")
            running = self.submit(plugin_workchain, **inputs)
            self.report(f"launching plugin {name} <{running.pk}>")
            plugin_running[name] = running

        return ToContext(**plugin_running)

    def inspect_plugin(self):
        """Verify that the `pluginWorkChain` finished successfully."""
        self.report(f"Inspect plugins: {self.ctx.keys()}")
        for name, entry_point in self.ctx.plugin_entries.items():
            if not self.should_run_plugin(name):
                continue
            workchain = self.ctx[name]
            if not workchain.is_finished_ok:
                self.report(
                    f"Plugin {name} WorkChain failed with exit status {workchain.exit_status}"
                )
                return self.exit_codes.get(f"ERROR_SUB_PROCESS_FAILED_{name}")
            # Attach the output nodes directly as outputs of the workchain.
            self.out_many(
                self.exposed_outputs(
                    workchain, entry_point["workchain"], namespace=name
                )
            )

    def results(self):
        """Add the results to the outputs."""

        self.report("workchain successfully completed")

    def on_terminated(self):
        """Clean the working directories of all child calculations if `clean_workdir=True` in the inputs."""
        super().on_terminated()

        if self.inputs.clean_workdir.value is False:
            self.report("remote folders will not be cleaned")
            return

        cleaned_calcs = []

        for called_descendant in self.node.called_descendants:
            if isinstance(called_descendant, orm.CalcJobNode):
                try:
                    called_descendant.outputs.remote_folder._clean()  # pylint: disable=protected-access
                    cleaned_calcs.append(called_descendant.pk)
                except (OSError, KeyError):
                    pass

        if cleaned_calcs:
            self.report(
                f"cleaned remote folders of calculations: {' '.join(map(str, cleaned_calcs))}"
            )
