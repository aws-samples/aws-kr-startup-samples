import sys
import argparse
import traceback

from sh import cp, find, mkdir, wget


def main():
  parser = argparse.ArgumentParser()

  parser.add_argument("--domain", type=str, default="sagemaker.readthedocs.io")
  parser.add_argument("--website", type=str, default="https://sagemaker.readthedocs.io/en/stable/")
  parser.add_argument("--output-dir", type=str, default="docs")
  parser.add_argument("--dryrun", action='store_true')
  args, _ = parser.parse_known_args()

  WEBSITE, DOMAIN, KB_DIR = (args.website, args.domain, args.output_dir)

  if args.dryrun:
    print(f"WEBSITE={WEBSITE}, DOMAIN={DOMAIN}, OUTPUT_DIR={KB_DIR}", file=sys.stderr)
    sys.exit(0)

  mkdir('-p', KB_DIR)

  try:
    WGET_ARGUMENTS = f"-e robots=off --recursive --no-clobber --page-requisites --html-extension --convert-links --restrict-file-names=windows --domains {DOMAIN} --no-parent {WEBSITE}"
    wget_argument_list = WGET_ARGUMENTS.split()
    wget(*wget_argument_list)
  except Exception as ex:
    traceback.print_exc()

  results = find(DOMAIN, '-name', '*.html')
  html_files = results.strip('\n').split('\n')
  for each in html_files:
    flat_i = each.replace('/', '-')
    cp(each, f"{KB_DIR}/{flat_i}")

  print(f"There are {len(html_files)} files in {KB_DIR} directory", file=sys.stderr)


if __name__ == "__main__":
  main()