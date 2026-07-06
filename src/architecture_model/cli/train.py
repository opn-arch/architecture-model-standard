"""Training CLI commands — moved to arch-agent package."""


def register_train_commands(subparsers):
    """Register training subcommands (stub — see arch-agent package)."""
    parser = subparsers.add_parser(
        "train",
        help="Training commands (moved to arch-agent package)"
    )
    parser.set_defaults(func=_train_stub)


def _train_stub(args):
    print("Training commands have moved to the arch-agent package.")
    print("Install: pip install arch-agent")
    print("Run: arch-agent train --help")
