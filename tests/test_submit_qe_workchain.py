from aiidalab_qe.app.wizard_app import WizardApp


def test_create_builder_default(
    data_regression,
    submit_app_generator,
):
    """ "Test the creation of the workchain builder.

    metal, non-magnetic
    """

    app: WizardApp = submit_app_generator(properties=["bands", "pdos"])

    parameters = app.submit_model.get_model_state()
    app.submit_model._create_builder(parameters)
    # since uuid is specific to each run, we remove it from the output
    ui_parameters = remove_uuid_fields(parameters)
    remove_code_options(ui_parameters)
    # regression test for the parameters generated by the app
    # this parameters are passed to the workchain
    data_regression.check(ui_parameters)
    # test if create builder successfully
    # app.submit_model._create_builder(ui_parameters)  # TODO what are we doing here?
    # In the future, we will check the builder parameters using regresion test


def test_create_process_label(submit_app_generator):
    """Test the creation of the correct process label."""
    app: WizardApp = submit_app_generator(properties=["bands", "pdos"])
    app.submit_model.update_process_label()

    assert (
        app.submit_model.process_label
        == "Si2 [relax: atoms+cell, balanced protocol] → bands, pdos"
    )
    # suppose we change the label of the structure:
    app.submit_model.input_structure.label = "Si2, unit cell"
    app.submit_model.update_process_label()
    assert (
        app.submit_model.process_label
        == "Si2, unit cell [relax: atoms+cell, balanced protocol] → bands, pdos"
    )
    # suppose by mistake we provide an empty label, we then fallback to use the formula:
    app.submit_model.input_structure.label = ""
    app.submit_model.update_process_label()
    assert (
        app.submit_model.process_label
        == "Si2 [relax: atoms+cell, balanced protocol] → bands, pdos"
    )


def test_create_builder_insulator(
    submit_app_generator,
):
    """ "Test the creation of the workchain builder.

    insulator, non-magnetic, no smearing
    the occupation type is set to fixed, smearing and degauss should not be set"""

    app: WizardApp = submit_app_generator(
        electronic_type="insulator", properties=["bands", "pdos"]
    )
    parameters = app.submit_model.get_model_state()
    builder = app.submit_model._create_builder(parameters)

    # check and validate the builder
    got = builder_to_readable_dict(builder)

    assert (
        got["bands"]["bands"]["scf"]["pw"]["parameters"]["SYSTEM"]["occupations"]
        == "fixed"
    )
    assert "smearing" not in got["bands"]["bands"]["scf"]["pw"]["parameters"]["SYSTEM"]


def test_create_builder_advanced_settings(
    submit_app_generator,
):
    """Test the creation of the workchain builder with advanced settings

    -metal
    -collinear
    -tot_charge
    -initial_magnetic_moments
    -vdw_corr
    -electron_maxstep
    -properties: bands, pdos
    """

    app: WizardApp = submit_app_generator(
        electronic_type="metal",
        spin_type="collinear",
        tot_charge=1.0,
        vdw_corr="dft-d3bj",
        initial_magnetic_moments=0.1,
        electron_maxstep=100,
        properties=["bands", "pdos"],
    )
    parameters = app.submit_model.get_model_state()
    builder = app.submit_model._create_builder(parameters)

    # check if the AiiDA nodes are passed to the plugins instead of copied, take psuedos as an example
    assert (
        builder.relax.base.pw.pseudos["Si"].uuid
        == builder.bands.bands.scf.pw.pseudos["Si"].uuid
    )
    assert (
        builder.relax.base.pw.pseudos["Si"].uuid
        == builder.pdos.scf.pw.pseudos["Si"].uuid
    )

    # check and validate the builder
    got = builder_to_readable_dict(builder)

    # test tot_charge is updated in the three steps
    for parameters in [
        got["relax"]["base"],
        got["bands"]["bands"]["scf"],
        got["pdos"]["scf"],
        got["pdos"]["nscf"],
    ]:
        assert parameters["pw"]["parameters"]["SYSTEM"]["tot_charge"] == 1.0
        assert parameters["pw"]["parameters"]["SYSTEM"]["vdw_corr"] == "dft-d3"
        assert parameters["pw"]["parameters"]["SYSTEM"]["dftd3_version"] == 4
        assert parameters["pw"]["parameters"]["ELECTRONS"]["electron_maxstep"] == 100

    # test initial_magnetic_moments set 'starting_magnetization' in pw.in
    assert (
        got["relax"]["base"]["pw"]["parameters"]["SYSTEM"]["starting_magnetization"][
            "Si"
        ]
        == 0.025
    )


def test_warning_messages(
    generate_structure_data,
    submit_app_generator,
):
    """Test the creation of the warning messages.

    For now, we test that the suggestions are indeed there.
    We should check the whole message, but this is for now not easy to do: the message is built
    on the fly with variables which are not accessible in this namespace.
    """
    import os

    suggestions = {
        "more_resources": "Increase the resources",
        "change_configuration": "Review the configuration",
        "go_remote": "Select a code that runs on a larger machine",
        "avoid_overloading": "Reduce the number of CPUs to avoid the overloading of the local machine",
    }

    app: WizardApp = submit_app_generator(properties=["bands", "pdos"])
    submit_model = app.submit_model
    global_model = submit_model.get_model("global")

    pw_code = global_model.get_model("quantumespresso__pw")

    # we increase the resources, so we should have the Warning-3
    pw_code.num_cpus = len(os.sched_getaffinity(0))
    global_model.check_resources()
    for suggestion in ["avoid_overloading", "go_remote"]:
        assert suggestions[suggestion] in submit_model.warning_messages

    # now we use a large structure, so we should have the Warning-1 (and 2 if not on localhost)
    structure = generate_structure_data("H2O-larger")
    submit_model.input_structure = structure
    pw_code.num_cpus = 1
    global_model.check_resources()
    num_sites = len(structure.sites)
    volume = structure.get_cell_volume()
    estimated_CPUs = global_model._estimate_min_cpus(num_sites, volume)
    assert estimated_CPUs == 2
    for suggestion in ["more_resources", "change_configuration"]:
        assert suggestions[suggestion] in submit_model.warning_messages


def builder_to_readable_dict(builder):
    """transverse the builder and return a dictionary with readable values."""
    from aiida import orm
    from aiida.engine import ProcessBuilderNamespace
    from aiida.plugins import DataFactory

    UpfData = DataFactory("pseudo.upf")

    ignore_keys = ["metadata", "monitors", "code", "structure"]

    readable_dict = {}
    for k, v in builder.items():
        if k in ignore_keys:
            continue
        if isinstance(v, UpfData):
            readable_dict[k] = v.filename
        elif isinstance(v, (dict, ProcessBuilderNamespace)):
            readable_dict[k] = builder_to_readable_dict(v)
        elif isinstance(v, orm.Dict):
            readable_dict[k] = v.get_dict()
        elif isinstance(v, (orm.Int, orm.Float, orm.Str, orm.Bool)):
            readable_dict[k] = v.value
        elif isinstance(v, orm.List):
            readable_dict[k] = v.get_list()
        else:
            readable_dict[k] = v

    return readable_dict


def remove_uuid_fields(data):
    """
    Recursively remove fields that contain UUID values from a dictionary.

    :param data: The dictionary to process.
    :return: The dictionary with UUID fields removed.
    """
    import re

    # Define a UUID pattern
    uuid_pattern = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", re.I
    )

    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # If the value matches the UUID pattern, skip adding it to the new dictionary
            if isinstance(value, str) and uuid_pattern.match(value):
                continue
            # Otherwise, process the value recursively and add it to the new dictionary
            else:
                new_dict[key] = remove_uuid_fields(value)
        return new_dict
    elif isinstance(data, list):
        # Process each item in the list recursively
        return [remove_uuid_fields(item) for item in data]
    else:
        # Return the value unchanged if it's not a dictionary or list
        return data


def remove_code_options(parameters):
    """Remove the code options from the parameters."""
    for panel in parameters["codes"].values():  # type: ignore
        for code in panel["codes"].values():
            del code["options"]
