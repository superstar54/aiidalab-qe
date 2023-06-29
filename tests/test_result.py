def test_workchainview(generate_qeapp_workchain):
    from aiidalab_qe.app.result.node_view import WorkChainViewer

    wkchain = generate_qeapp_workchain()
    wcv = WorkChainViewer(wkchain.node)
    assert len(wcv.result_tabs.children) == 5
    assert wcv.result_tabs._titles["0"] == "Workflow Summary"
    assert wcv.result_tabs._titles["1"] == "Final Geometry"
    assert wcv.result_tabs._titles["2"] == "Electronic Structure"


def test_summary_view(generate_qeapp_workchain):
    """test the report can be properly generated from the builder without errors"""
    from aiidalab_qe.app.result.node_view import WorkChainViewer

    wkchain = generate_qeapp_workchain()
    wcv = WorkChainViewer(wkchain.node)
    print(wcv.result_tabs.children[0].children[0].children[0])
    # assert "None" not in report_html
    assert "None" not in wcv.result_tabs.children[0].children[0].children[0].value
