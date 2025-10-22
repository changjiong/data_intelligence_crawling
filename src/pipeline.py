#!/usr/bin/env python
import argparse, sys
from rich import print
from dotenv import load_dotenv

def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tasks = [
        "policies_npc (zxkc, ggjrdn enterprisesPolicies)",
        "finreg (wechat article/pdf)",
        "bank_tech_finance (extract metrics 2023/2024)",
        "peer_products (ggjrdn + csv imports)",
        "investment_itjuzi (recent 1y)",
    ]
    if args.dry_run:
        print("[bold cyan]计划任务：[/]")
        for t in tasks:
            print(f" - {t}")
        sys.exit(0)
    print("[yellow]TODO：实现真实任务编排与运行[/]")

if __name__ == "__main__":
    main()
