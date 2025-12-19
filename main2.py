import argparse
import os
import time
from pathlib import Path

from colorama import Fore

from extractors.general import GeneralExtractor
from extractors.hianime import HianimeExtractor
from extractors.instagram import InstagramExtractor


class Main:
    def __init__(self):
        self.args = self.parse_args()
        Path(self.args.output_dir).mkdir(parents=True, exist_ok=True)

        jobs = self.build_jobs()

        if not jobs:
            print(f"{Fore.RED}No links/search terms provided. Nothing to do.{Fore.RESET}")
            return

        total = len(jobs)
        for idx, item in enumerate(jobs, start=1):
            per_start = time.time()

            # Make a fresh args object per job (prevents accidental mutation bleed-over)
            job_args = argparse.Namespace(**vars(self.args))

            # Each item is either a URL (http/https) or a search term
            if item.lower().startswith(("http://", "https://")):
                job_args.link = item
                # If user supplied a base filename and we're doing a batch, make it unique per job
                if job_args.filename and total > 1:
                    job_args.filename = f"{job_args.filename}_{idx:03d}"
            else:
                job_args.link = None
                job_args.filename = item  # treat as hianime search term

            print(
                f"{Fore.LIGHTCYAN_EX}[{idx}/{total}] Processing: {item}{Fore.RESET}"
            )

            try:
                extractor = self.get_extractor(job_args)
                extractor.run()
            except Exception as e:
                print(f"{Fore.RED}Failed: {item}\n  -> {e}{Fore.RESET}")
                if not self.args.continue_on_error:
                    raise
            finally:
                per_elapsed = time.time() - per_start
                print(
                    f"{Fore.LIGHTGREEN_EX}Done [{idx}/{total}] in "
                    f"{int(per_elapsed // 60)}:{int(per_elapsed % 60):02d}{Fore.RESET}\n"
                )

    def get_extractor(self, args):
        # Interactive mode only if nothing provided via args
        if not args.link and not args.filename:
            os.system("cls" if os.name == "nt" else "clear")
            print(f"{Fore.LIGHTGREEN_EX}GDown {Fore.LIGHTCYAN_EX}Downloader{Fore.RESET}\n")
            print("Paste links/search terms (one per line). Blank line to start.\n")

            items = []
            while True:
                line = input(f"{Fore.LIGHTYELLOW_EX}> {Fore.RESET}").strip()
                if not line:
                    break
                items.append(line)

            # If user pasted multiple, run them as a batch immediately
            if len(items) > 1:
                self.args.link = []  # not used anymore, but keep consistent
                # Run a nested batch using the same preferences
                for i, it in enumerate(items, start=1):
                    job_args = argparse.Namespace(**vars(self.args))
                    if it.lower().startswith(("http://", "https://")):
                        job_args.link = it
                        if job_args.filename and len(items) > 1:
                            job_args.filename = f"{job_args.filename}_{i:03d}"
                    else:
                        job_args.link = None
                        job_args.filename = it

                    extractor = self.get_extractor(job_args)
                    extractor.run()
                return GeneralExtractor(args=args)  # unreachable in practice, but keeps typing calm

            # Single entry fallback
            ans = items[0] if items else ""
            if ans.lower().startswith(("http://", "https://")):
                args.link = ans
            else:
                return HianimeExtractor(args=args, name=ans)

        # Existing behaviors
        if not args.link and args.filename:
            return HianimeExtractor(args=args, name=args.filename)

        if args.link and "hianime" in args.link:
            return HianimeExtractor(args=args)
        if args.link and "instagram.com" in args.link:
            return InstagramExtractor(args=args)

        return GeneralExtractor(args=args)

    def build_jobs(self):
        jobs = []

        # From repeated -l / --link
        if self.args.link:
            jobs.extend(self.args.link)

        # From --links-file
        if self.args.links_file:
            p = Path(self.args.links_file)
            if not p.exists():
                raise FileNotFoundError(f"links file not found: {p}")
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                jobs.append(line)

        # If user provided -n/--filename but no links, treat it as a single search term (old behavior)
        if not jobs and self.args.filename and not self.args.link:
            jobs.append(self.args.filename)

        # De-dupe while preserving order
        seen = set()
        out = []
        for j in jobs:
            if j not in seen:
                seen.add(j)
                out.append(j)
        return out

    def parse_args(self):
        parser = argparse.ArgumentParser(description="Anime downloader options")

        parser.add_argument(
            "--no-subtitles",
            action="store_true",
            help="Skip downloading subtitle files (.vtt)",
        )

        parser.add_argument(
            "-o",
            "--output-dir",
            type=str,
            default="output",
            help="Directory to save downloaded files",
        )

        parser.add_argument(
            "-n",
            "--filename",
            type=str,
            default="",
            help="Used for name of anime, or base name of output file when using other extractor",
        )

        parser.add_argument(
            "--aria",
            action="store_true",
            default=False,
            help="Use aria2c as external downloader",
        )

        # ✅ repeatable link argument: -l url1 -l url2 -l url3
        parser.add_argument(
            "-l",
            "--link",
            action="append",
            default=[],
            help="Provide link to desired content (repeatable)",
        )

        # ✅ file input: one URL/search term per line
        parser.add_argument(
            "--links-file",
            type=str,
            default=None,
            help="Path to text file with one URL/search term per line",
        )

        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continue batch even if one item fails",
        )

        parser.add_argument(
            "--server", type=str, default=None, help="Streaming Server to download from"
        )

        return parser.parse_args()


if __name__ == "__main__":
    start = time.time()
    Main()
    elapsed = time.time() - start
    print(f"Took {int(elapsed / 60)}:{int((elapsed % 60)):02d} to finish")
