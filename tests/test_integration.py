"""Integration tests, run against StudioNet.

    pip install genlayer-py==0.18.0
    GENLAYER_STUDIO=1 pytest tests/test_integration.py -v

They are opt in. Without GENLAYER_STUDIO set they skip, so `pytest tests/ -q`
stays clean and offline on a reviewer's machine whatever is installed there,
and an unreachable network can never be mistaken for a broken contract.

They exercise the deterministic half on a real runtime, where the simulator is
weakest: the sender is derived from a signature rather than set by a test, the
fee is real value attached to a real transaction, and the free refusals
before any fetch are shown to cost no inference. A check itself costs a
fetch and inference on every validator and is on the record
from scripts/demo.py.
"""

import os
import pathlib
import sys

import pytest

if not os.environ.get("GENLAYER_STUDIO"):
    pytest.skip("integration tests run against StudioNet and are opt in: set GENLAYER_STUDIO=1. "
                "Everything else runs offline with pytest tests/ -q", allow_module_level=True)

pytest.importorskip("genlayer_py", reason="pip install genlayer-py==0.18.0")

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent.parent / "scripts"))
from studio import Studio                                     # noqa: E402

CODE = (pathlib.Path(__file__).absolute().parent.parent / "contracts" / "stalecheck.py").read_text(encoding="utf-8")
TITLE = "Stalecheck, integration run"
URL = "https://example.com/guide"
FEE = 10 ** 13


@pytest.fixture(scope="module")
def world():
    s = Studio()
    funder = s.account("funder", gen=1)
    maintainer = s.account("maintainer")
    address = s.deploy(funder, CODE, [])
    s.write(funder, address, "open", [maintainer.address, TITLE, URL, 30, 2, 3600], value=FEE, step="open a plan")
    return s, address, funder, maintainer


def test_a_plan_opens_with_the_signer_as_funder_and_the_fee_held(world):
    s, address, funder, maintainer = world
    p = s.read(address, "plan", [0])
    assert p["status"] == "open" and p["funder"].lower() == funder.address.lower()
    assert p["maintainer"].lower() == maintainer.address.lower()
    assert p["total"] == str(FEE) and int(s.read(address, "held_total")) == FEE
    assert p["installment_amounts"] == [str(FEE // 2), str(FEE - FEE // 2)]


def test_the_funder_cannot_check(world):
    s, address, funder, _ = world
    row = s.write(funder, address, "check", [0], step="the funder checks", expect="refused")
    assert "only the named maintainer may check" in row["refusal"]


def test_a_close_while_the_schedule_runs_is_refused(world):
    s, address, _, maintainer = world
    row = s.write(maintainer, address, "close", [0], step="close too early", expect="refused")
    assert "the schedule runs until" in row["refusal"]


def test_an_unknown_plan_is_a_refusal_not_the_newest_row(world):
    s, address, _, maintainer = world
    row = s.write(maintainer, address, "close", [99], step="close a plan that does not exist", expect="refused")
    assert "no such plan" in row["refusal"]