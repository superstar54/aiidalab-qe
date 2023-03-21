#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Example script to submit a ``PwCalculation`` or ``PwBaseWorkChain`` over the web API."""
from __future__ import annotations

import os
import typing as t

import click
import requests

BASE_URL = "http://127.0.0.1:8000"


def echo_error(message: str) -> None:
    """Echo the message prefixed with ``Error`` in bold red.

    :param message: The error message to echo.
    """
    click.echo(click.style("Error: ", fg="red", bold=True), nl=False)
    click.echo(message)


def request(
    url,
    json: dict[str, t.Any] | None = None,
    data: dict[str, t.Any] | None = None,
    method="POST",
) -> dict[str, t.Any] | None:
    """Perform a request to the web API of ``aiida-restapi``.

    If the ``ACCESS_TOKEN`` environment variable is defined, it is passed in the ``Authorization`` header.

    :param url: The relative URL path without leading slash, e.g., `nodes`.
    :param json: A JSON serializable dictionary to send in the body of the request.
    :param data: Dictionary, list of tuples, bytes, or file-like object to send in the body of the request.
    :param method: The request method, POST by default.
    :returns: The response in JSON or ``None``.
    """
    access_token = os.getenv("ACCESS_TOKEN", None)

    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
    else:
        headers = {}

    response = requests.request(
        method, f"{BASE_URL}/{url}", json=json, data=data, headers=headers
    )

    try:
        response.raise_for_status()
    except requests.HTTPError:
        results = response.json()

        echo_error(f"{response.status_code} {response.reason}")

        if "detail" in results:
            echo_error(results["detail"])

        for error in results.get("errors", []):
            click.echo(error["message"])

        return None
    else:
        return response.json()


def authenticate(
    username: str = "johndoe@example.com", password: str = "secret"
) -> str | None:
    """Authenticate with the web API to obtain an access token.

    Note that if authentication is successful, the access token is stored in the ``ACCESS_TOKEN`` environment variable.

    :param username: The username.
    :param password: The password.
    :returns: The access token or ``None`` if authentication was unsuccessful.
    """
    results = request("token", data={"username": username, "password": password})

    if results:
        access_token = results["access_token"]
        os.environ["ACCESS_TOKEN"] = access_token
        return access_token

    return None


def get_pseudo_family_pseudos(pseudo_family_label: str) -> dict[str, t.Any] | None:
    """Return the pseudo potentials in the given family.

    :param pseudo_family_label: The label of the pseudopotential family.
    :returns: The pseudopotential family and the pseudos it contains.
    """
    variables = {"label": pseudo_family_label}
    query = """
        query function($label: String) {
            group(label: $label) {
                uuid
                label
                nodes {
                    rows {
                        uuid
                        attributes
                    }
                }
            }
        }
    """
    results = request("graphql", {"query": query, "variables": variables})

    if results:
        return results["data"]["group"]

    return None


def get_pseudo_for_element(
    pseudo_family_label: str, element: str
) -> dict[str, t.Any] | None:
    """Return the pseudo potential for a given pseudo potential family and element.

    :param pseudo_family_label: The label of the pseudopotential family.
    :param element: The element for which to retrieve a pseudopotential.
    :returns: The pseudopotential if found, or ``None`` otherwise.
    """
    family = get_pseudo_family_pseudos(pseudo_family_label)

    if family is None:
        return None

    pseudo = None

    for row in family["nodes"]["rows"]:
        if row["attributes"]["element"] == element:
            pseudo = row
            break

    return pseudo


def create_node(entry_point: str, attributes: dict[str, t.Any]) -> str | None:
    """Create a ``Node`` and return the UUID if successful or ``None`` otherwise.

    :param entry_point: The entry point name of the node type to create.
    :param attributes: The attributes to set.
    :returns: The UUID of the created node or ``None`` if it failed.
    """
    data = {
        "entry_point": entry_point,
        "attributes": attributes,
    }
    result = request("nodes", data)

    if result:
        return result["uuid"]

    return None


def get_code(default_calc_job_plugin: str) -> dict[str, t.Any] | None:
    """Return a code that has the given default calculation job plugin.

    Returns the first code that is matched.

    :param default_calc_job_plugin: The default calculation job plugin the code should have.
    :raises ValueError: If no code could be found.
    """
    variables = {"default_calc_job_plugin": default_calc_job_plugin}
    query = """
        {
            nodes(filters: "node_type ILIKE 'data.core.code.installed.InstalledCode%'") {
                rows {
                    uuid
                    label
                    attributes
                }
            }
        }
    """
    results = request("graphql", {"query": query, "variables": variables})

    if results is None:
        return None

    node = None

    for row in results["data"]["nodes"]["rows"]:
        if row["attributes"]["input_plugin"] == default_calc_job_plugin:
            node = row

    if node is None:
        raise ValueError(
            f"No code with default calculation job plugin `{default_calc_job_plugin}` found."
        )

    return node


def get_node_uuid(inputs):
    from aiida.engine.processes.builder import ProcessBuilderNamespace
    from aiida.orm import Node

    new_inputs = {}
    for key, value in inputs.items():
        # print(key, type(value))
        if isinstance(value, Node):
            if not value.is_stored:
                value.store()
            # print(key, value.uuid)
            new_inputs[f"{key}.uuid"] = value.uuid
        elif isinstance(value, dict):
            new_inputs[key] = get_node_uuid(value)
        elif isinstance(value, ProcessBuilderNamespace):
            value = value._inputs()
            new_inputs[key] = get_node_uuid(value)
        else:
            new_inputs[key] = value
    return new_inputs


def restapi_submit(builder):
    """Authenticate with the web API and submit a ``PwCalculation`` or ``PwBaseWorkChain``."""
    token = authenticate()

    if token is None:
        echo_error("Could not authenticate with the API, aborting")
        return

    parameters = builder._inputs(prune=True)
    parameters = get_node_uuid(parameters)
    inputs = {
        "label": "Test AiiDA RESTAPI using AiiDAlab",
        "process_entry_point": "aiida.workflows:aiidalab_qe_workchain.base",
        "inputs": parameters,
    }
    results = request("processes", json=inputs)
    click.echo(f'Successfuly submitted process with pk<{results["id"]}>')
    return results["uuid"]


def restapi_load_node(process_uuid: str) -> dict[str, t.Any]:
    results = request(f"processes/uuid/{process_uuid}", method="GET")
    return results


def restapi_get_inputs(process_uuid: str) -> dict[str, t.Any]:
    """Return a dictionary of the inputs of the process with the given ID.

    :param process_uuid: The ID of the process.
    :return: Dictionary of the inputs where keys are link labels and values are dictionaries containing the node's uuid
        and attributes.
    """
    query = """
        query function($process_uuid: String) {
            node(uuid: $process_uuid) {
                incoming {
                    rows {
                        node {
                            uuid
                            attributes
                        }
                        link {
                            label
                        }
                    }
                }
            }
        }
    """
    variables = {"process_uuid": process_uuid}
    results = request("graphql", {"query": query, "variables": variables})

    inputs = {}

    for value in results["data"]["node"]["incoming"]["rows"]:
        link_label = value["link"]["label"]
        inputs[link_label] = {
            "uuid": value["node"]["uuid"],
            "attributes": value["node"]["attributes"],
        }

    return inputs


def restapi_get_outputs(process_uuid: str) -> dict[str, t.Any]:
    """Return a dictionary of the outputs of the process with the given ID.

    :param process_uuid: The ID of the process.
    :return: Dictionary of the outputs where keys are link labels and values are dictionaries containing the node's uuid
        and attributes.
    """
    query = """
        query function($process_uuid: String) {
            node(uuid: $process_uuid) {
                outgoing {
                    rows {
                        node {
                            uuid
                            attributes
                        }
                        link {
                            label
                        }
                    }
                }
            }
        }
    """
    variables = {"process_uuid": process_uuid}
    results = request("graphql", {"query": query, "variables": variables})

    outputs = {}

    for value in results["data"]["node"]["outgoing"]["rows"]:
        link_label = value["link"]["label"]
        outputs[link_label] = {
            "uuid": value["node"]["uuid"],
            "attributes": value["node"]["attributes"],
        }

    return outputs


if __name__ == "__main__":
    # restapi_submit()  # pylint: disable=no-value-for-parameter
    from pprint import pprint

    process = "ecbeec0d-316a-4b6a-bbd1-0864010b0db1"
    inputs = restapi_get_inputs(process)
    print("=" * 60)
    pprint(inputs)
    outputs = restapi_get_outputs(process)
    print("=" * 60)
    pprint(outputs)
    node = restapi_load_node(process)
    print("=" * 60)
    print(node)
