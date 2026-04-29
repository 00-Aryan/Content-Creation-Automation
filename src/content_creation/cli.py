import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description="Content Creation Factory CLI - Phase: Setup/Bootstrap"
    )
    
    # Placeholder for future commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Collect command stub
    collect_parser = subparsers.add_parser("collect", help="Ingest topics from sources")
    collect_parser.add_argument("--source", type=str, help="Specific source to collect (e.g., arxiv)")
    collect_parser.add_argument("--all", action="store_true", help="Collect from all sources")
    
    # Status command stub
    subparsers.add_parser("status", help="Check system and ingestion status")
    
    args = parser.parse_args()
    
    if args.command == "collect":
        print(f"STUB: Collecting from source: {args.source if args.source else 'all'}")
        print("Feature implementation planned for Week 1 Task: Source Ingestion.")
    elif args.command == "status":
        print("Content Creation Factory - Status: Setup Phase")
        print("Documentation: OK")
        print("Schemas: OK")
        print("Implementation: Awaiting Week 1 feature logic.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
