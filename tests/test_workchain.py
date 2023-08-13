from aiida import engine, orm
from aiida.common import LinkType


def test_qeapp_workchain(generate_qeapp_workchain):
    wkchain = generate_qeapp_workchain()
    print("wkchain: ", wkchain)
    assert wkchain.setup() is None
    # generate structure for scf calculation
    #
    assert wkchain.should_run_relax() is True
    wkchain.setup()
    assert len(wkchain.ctx.plugin_entries) == 2
    # run relax and return the process
    relax_process = wkchain.run_relax()["workchain_relax"]
    # run plugin and return the process
    processes = wkchain.run_plugin()
    bands_process = processes["bands"]
    pdos_process = processes["pdos"]
    # add test result
    result = orm.Dict({"energy": 0})
    result.store()
    result.base.links.add_incoming(
        relax_process, link_type=LinkType.RETURN, link_label="output_parameters"
    )
    result.base.links.add_incoming(
        bands_process, link_type=LinkType.RETURN, link_label="output_parameters"
    )
    result.base.links.add_incoming(
        pdos_process, link_type=LinkType.RETURN, link_label="output_parameters"
    )
    # set state to finished.
    relax_process.set_process_state(engine.ProcessState.FINISHED)
    relax_process.set_exit_status(0)
    bands_process.set_process_state(engine.ProcessState.FINISHED)
    bands_process.set_exit_status(0)
    pdos_process.set_process_state(engine.ProcessState.FINISHED)
    pdos_process.set_exit_status(0)
    wkchain.ctx["workchain_relax"] = relax_process
    wkchain.ctx["workchain_bands"] = bands_process
    wkchain.ctx["workchain_pdos"] = pdos_process
    qeapp_node = wkchain.node
    qeapp_node.set_exit_status(0)
    qeapp_node.set_process_state(engine.ProcessState.FINISHED)
