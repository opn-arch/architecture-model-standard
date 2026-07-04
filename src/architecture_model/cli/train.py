"""
CLI commands for the training pipeline.

Registers the 'train' subcommand group with sub-subcommands:
    fetch, run, fit, swap, loop, status
"""

from __future__ import annotations

import argparse


def register_train_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the 'train' command group with its sub-subcommands."""
    p_train = subparsers.add_parser(
        "train",
        help="Training pipeline commands",
        description="Commands for the MPC training loop: fetch repos, run iterations, fit models.",
    )
    train_sub = p_train.add_subparsers(dest="train_command", help="Training subcommands")

    # --- train fetch ---
    p_fetch = train_sub.add_parser("fetch", help="Discover and clone repositories for training")
    p_fetch.add_argument("--n", type=int, default=50, help="Number of repos to fetch (default: 50)")
    p_fetch.add_argument("--min-stars", type=int, default=100, help="Minimum GitHub stars (default: 100)")
    p_fetch.add_argument("--clone-dir", default="./repos", help="Directory to clone repos into (default: ./repos)")

    # --- train run ---
    p_run = train_sub.add_parser("run", help="Run a single pipeline iteration")
    p_run.add_argument("--n-repos", type=int, default=50, help="Number of repos per iteration (default: 50)")
    p_run.add_argument("--db", default="training.db", help="Path to training database (default: training.db)")

    # --- train fit ---
    p_fit = train_sub.add_parser("fit", help="Prepare dataset and train the surrogate model")
    p_fit.add_argument("--db", default="training.db", help="Path to training database (default: training.db)")
    p_fit.add_argument("--base-model", default="codellama:13b", help="Base model for fine-tuning (default: codellama:13b)")
    p_fit.add_argument("--epochs", type=int, default=3, help="Number of training epochs (default: 3)")

    # --- train swap ---
    p_swap = train_sub.add_parser("swap", help="Swap the active surrogate model")
    p_swap.add_argument("--model-name", default="arch-model-v1", help="Name of the model to activate (default: arch-model-v1)")

    # --- train loop ---
    p_loop = train_sub.add_parser("loop", help="Run the full MPC training loop")
    p_loop.add_argument("--max-iterations", type=int, default=100, help="Maximum loop iterations (default: 100)")
    p_loop.add_argument("--budget", type=int, default=100000, help="Oracle token budget (default: 100000)")

    # --- train status ---
    p_status = train_sub.add_parser("status", help="Show training pipeline status")
    p_status.add_argument("--db", default="training.db", help="Path to training database (default: training.db)")


def _cmd_train(args) -> int:
    """Dispatch train sub-subcommands."""
    if not hasattr(args, "train_command") or not args.train_command:
        # No subcommand given — print help
        print("usage: architecture-model train <command> [options]")
        print()
        print("Training subcommands:")
        print("  fetch    Discover and clone repositories for training")
        print("  run      Run a single pipeline iteration")
        print("  fit      Prepare dataset and train the surrogate model")
        print("  swap     Swap the active surrogate model")
        print("  loop     Run the full MPC training loop")
        print("  status   Show training pipeline status")
        return 1

    handlers = {
        "fetch": _cmd_train_fetch,
        "run": _cmd_train_run,
        "fit": _cmd_train_fit,
        "swap": _cmd_train_swap,
        "loop": _cmd_train_loop,
        "status": _cmd_train_status,
    }
    return handlers[args.train_command](args)


def _cmd_train_fetch(args) -> int:
    """Discover and clone repositories for training data."""
    print(f"Fetching repos: n={args.n}, min_stars={args.min_stars}, clone_dir={args.clone_dir}")
    return 0


def _cmd_train_run(args) -> int:
    """Run a single pipeline iteration."""
    print(f"Running iteration: n_repos={args.n_repos}, db={args.db}")
    return 0


def _cmd_train_fit(args) -> int:
    """Prepare dataset and train the surrogate model."""
    print(f"Training: db={args.db}, base_model={args.base_model}, epochs={args.epochs}")
    return 0


def _cmd_train_swap(args) -> int:
    """Swap the active surrogate model."""
    print(f"Swapping model to: {args.model_name}")
    return 0


def _cmd_train_loop(args) -> int:
    """Run the full MPC training loop."""
    print(f"Starting training loop: max_iterations={args.max_iterations}, budget={args.budget}")
    return 0


def _cmd_train_status(args) -> int:
    """Show training pipeline status."""
    print(f"Training status from: {args.db}")
    return 0
