from brownie import *
from pathlib import Path


# Execution Command Format:
# `brownie run scripts/br_deploy.py main "deployer" "ethereum" --network=eth-mainnet`
def main(deployer_account="deployer", network_cfg="ethereum"):
    deps = project.load(
        Path.home() / ".brownie" / "packages" / config["dependencies"][0]
    )

    config_contact = {
        "ethereum": {
            "default_admin": "",
            "minter": "",
            "recipient": "",
        },
        "holesky": {
            "default_admin": "0x0C99B08F2233b04066fe13A0A1Bf1474416fD77F",
            "minter": "0x0C99B08F2233b04066fe13A0A1Bf1474416fD77F",
            "recipient": "0x0C99B08F2233b04066fe13A0A1Bf1474416fD77F",
        },
    }

    assert config_contact[network_cfg]["default_admin"] != ""
    assert config_contact[network_cfg]["minter"] != ""
    assert config_contact[network_cfg]["recipient"] != ""
    deployer = accounts.load(deployer_account)

    br_contract = Bedrock.deploy(
        config_contact[network_cfg]["default_admin"],
        config_contact[network_cfg]["minter"],
        config_contact[network_cfg]["recipient"],
        {"from": deployer},
    )

    print("Bedrock contract address", br_contract)
    transparent_br = Contract.from_abi("Bedrock",br_contract.address, Bedrock.abi)
