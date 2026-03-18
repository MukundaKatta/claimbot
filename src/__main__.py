"""CLI for claimbot."""
import sys, json, argparse
from .core import Claimbot

def main():
    parser = argparse.ArgumentParser(description="ClaimBot — AI Insurance Claim Processor. Automated insurance claim assessment and processing.")
    parser.add_argument("command", nargs="?", default="status", choices=["status", "run", "info"])
    parser.add_argument("--input", "-i", default="")
    args = parser.parse_args()
    instance = Claimbot()
    if args.command == "status":
        print(json.dumps(instance.get_stats(), indent=2))
    elif args.command == "run":
        print(json.dumps(instance.analyze(input=args.input or "test"), indent=2, default=str))
    elif args.command == "info":
        print(f"claimbot v0.1.0 — ClaimBot — AI Insurance Claim Processor. Automated insurance claim assessment and processing.")

if __name__ == "__main__":
    main()
