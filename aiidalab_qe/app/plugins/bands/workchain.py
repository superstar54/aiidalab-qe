from aiida.orm import load_code
from aiida.plugins import WorkflowFactory
from aiida_quantumespresso.common.types import ElectronicType, RelaxType, SpinType

PwBandsWorkChain = WorkflowFactory("quantumespresso.pw.bands")


def get_builder(codes, structure, parameters):
    protocol = parameters["basic"].pop("protocol", "fast")
    pw_code = load_code(codes.get("pw_code"))
    overrides = {
        "scf": parameters["advanced"],
        "bands": parameters["advanced"],
    }
    relax_type = RelaxType(parameters["workflow"]["relax_type"])
    parameters["basic"]["electronic_type"] = ElectronicType(
        parameters["basic"]["electronic_type"]
    )
    parameters["basic"]["spin_type"] = SpinType(parameters["basic"]["spin_type"])
    parameters = parameters["basic"]
    builder = PwBandsWorkChain.get_builder_from_protocol(
        code=pw_code,
        structure=structure,
        protocol=protocol,
        overrides=overrides,
        **parameters,
    )
    builder.pop("relax")
    builder.pop("clean_workdir", None)
    return builder


workchain_and_builder = {"workchain": PwBandsWorkChain,
                         "exclude": ('clean_workdir', 'structure', 'relax'),
                         "get_builder": get_builder,
                         }
