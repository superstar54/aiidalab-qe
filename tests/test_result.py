def test_workchainview(qeapp_workchain):
    from aiidalab_qe.app.result.node_view import WorkChainViewer

    wkchain = qeapp_workchain
    wcv = WorkChainViewer(wkchain.node)
    assert len(wcv.result_tabs.children) == 4
    assert wcv.result_tabs._titles["0"] == "Workflow Summary"
    assert wcv.result_tabs._titles["1"] == "Final Geometry"
