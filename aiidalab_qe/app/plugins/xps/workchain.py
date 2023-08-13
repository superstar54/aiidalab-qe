from aiida.orm import Bool, Dict, Float, Group, QueryBuilder, load_code
from aiida.plugins import WorkflowFactory

XpsWorkChain = WorkflowFactory("quantumespresso.xps")


def get_builder(codes, structure, parameters):
    protocol = parameters["basic"].pop("protocol", "fast")
    xps_parameters = parameters.get("xps", {})
    all_correction_energies = xps_parameters.pop("correction_energies", {})
    elements_list = xps_parameters.pop("elements_list", None)
    # set core hole treatment for element
    core_hole_treatment = xps_parameters.pop("core_hole_treatment", "xch_smear")
    core_hole_treatments = {}
    for element in elements_list:
        core_hole_treatments[element] = core_hole_treatment
    # load pseudo for excited-state and group-state.
    pseudo_group = xps_parameters.pop("pseudo_group")
    pseudo_group = (
        QueryBuilder().append(Group, filters={"label": pseudo_group}).one()[0]
    )
    # set pseudo for element
    pseudos = {}
    elements = []
    correction_energies = {}
    for label in elements_list:
        element = label.split("_")[0]
        pseudos[element] = {
            "core_hole": [
                pseudo for pseudo in pseudo_group.nodes if pseudo.label == label
            ][0],
            "gipaw": [
                pseudo
                for pseudo in pseudo_group.nodes
                if pseudo.label == f"{element}_gs"
            ][0],
        }
        correction_energies[element] = all_correction_energies[label]["core"]
        elements.append(element)
    # TODO should we override the cutoff_wfc, cutoff_rho by the new pseudo?
    is_molecule_input = (
        True if xps_parameters.get("structure_type") == "molecule" else False
    )
    structure_preparation_settings = {
        "supercell_min_parameter": Float(3.0),
        "is_molecule_input": Bool(is_molecule_input),
    }
    if is_molecule_input:
        # kpoint
        # kpoints = KpointsData()
        # kpoints.set_kpoints_mesh([1, 1, 1])
        # parameters["advanced"]["kpoints"] = kpoints
        structure_preparation_settings["supercell_min_parameter"] = Float(8.0)
    pw_code = load_code(codes.get("pw_code"))
    overrides = {
        "ch_scf": parameters["advanced"],
    }
    parameters["basic"].update(xps_parameters)
    builder = XpsWorkChain.get_builder_from_protocol(
        code=pw_code,
        structure=structure,
        protocol=protocol,
        overrides=overrides,
        pseudos=pseudos,
        elements_list=elements,
        calc_binding_energy=Bool(True),
        correction_energies=Dict(correction_energies),
        core_hole_treatments=core_hole_treatments,
        structure_preparation_settings=structure_preparation_settings,
        **parameters,
    )
    builder.pop("relax")
    builder.pop("clean_workdir", None)
    # print("xps builder: ", builder)
    return builder


workchain_and_builder = {"workchain": XpsWorkChain,
                         "exclude": ('clean_workdir', 'structure', 'relax'),
                         "get_builder": get_builder,
                         }
