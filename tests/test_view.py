from aiidalab_qe.steps import ViewQeAppWorkChainStatusAndResultsStep


def test_view():
    view = ViewQeAppWorkChainStatusAndResultsStep()
    view.process = 16068
