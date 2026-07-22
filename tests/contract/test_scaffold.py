from lab.cli import build_parser


def test_lab_entrypoint_has_stable_name() -> None:
    assert build_parser().prog == "lab"
