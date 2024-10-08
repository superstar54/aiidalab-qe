from aiidalab_qe.setup.pseudos import PSEUDODOJO_VERSION, SSSP_VERSION


def test_protocol():
    """Test the protocol.
    The protocol from workchain_settings will trigger the
    update of the protocol in advanced_settings.
    """
    from aiidalab_qe.app.configuration import ConfigureQeAppWorkChainStep

    wg = ConfigureQeAppWorkChainStep()
    wg.workchain_settings.workchain_protocol.value = "fast"
    assert wg.advanced_settings.protocol == "fast"
    assert wg.advanced_settings.kpoints_distance.value == 0.5


def test_get_configuration_parameters():
    """Test the get_configuration_parameters method."""
    from aiidalab_qe.app.configuration import ConfigureQeAppWorkChainStep

    wg = ConfigureQeAppWorkChainStep()
    parameters = wg.get_configuration_parameters()
    parameters_ref = {
        "workchain": wg.workchain_settings.get_panel_value(),
        "advanced": wg.advanced_settings.get_panel_value(),
    }
    assert parameters == parameters_ref


def test_set_configuration_parameters():
    """Test the set_configuration_parameters method."""
    from aiidalab_qe.app.configuration import ConfigureQeAppWorkChainStep

    wg = ConfigureQeAppWorkChainStep()
    parameters = wg.get_configuration_parameters()
    parameters["workchain"]["relax_type"] = "positions"
    parameters["advanced"]["pseudo_family"] = f"SSSP/{SSSP_VERSION}/PBE/efficiency"
    wg.set_configuration_parameters(parameters)
    new_parameters = wg.get_configuration_parameters()
    assert parameters == new_parameters
    # test pseudodojo
    parameters["advanced"]["pseudo_family"] = (
        f"PseudoDojo/{PSEUDODOJO_VERSION}/PBEsol/SR/standard/upf"
    )
    wg.set_configuration_parameters(parameters)
    new_parameters = wg.get_configuration_parameters()
    assert parameters == new_parameters


def test_panel():
    """Dynamic add/remove the panel based on the workchain settings."""
    from aiidalab_qe.app.configuration import ConfigureQeAppWorkChainStep

    wg = ConfigureQeAppWorkChainStep()
    assert len(wg.tab.children) == 2
    parameters = wg.get_configuration_parameters()
    assert "bands" not in parameters
    wg.workchain_settings.properties["bands"].run.value = True
    assert len(wg.tab.children) == 3
    parameters = wg.get_configuration_parameters()
    assert "bands" in parameters


def test_reminder_info():
    """Dynamic add/remove the reminder text based on the workchain settings."""
    from aiidalab_qe.app.configuration import ConfigureQeAppWorkChainStep

    wg = ConfigureQeAppWorkChainStep()
    assert wg.workchain_settings.reminder_info["bands"].value == ""
    # select bands
    wg.workchain_settings.properties["bands"].run.value = True
    for name in wg.workchain_settings.reminder_info:
        if name == "bands":
            assert (
                wg.workchain_settings.reminder_info["bands"].value
                == "Customize bands settings in the panel above if needed."
            )
        else:
            # all other reminder texts should be empty
            assert wg.workchain_settings.reminder_info[name].value == ""
    # unselect bands
    wg.workchain_settings.properties["bands"].run.value = False
    assert wg.workchain_settings.reminder_info["bands"].value == ""
