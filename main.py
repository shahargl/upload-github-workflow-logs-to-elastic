import os
import requests
import io
import logging
import zipfile
import sys
import signal
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
# don't remove, it loads the configuration
import logger


def main():
    # User provided variables
    github_repo = os.environ.get("INPUT_GITHUB_REPOSITORY")
    try:
        assert github_repo not in (None, '')
    except:
        output = "The input github repository is not set"
        print(f"Error: {output}")
        sys.exit(-1)

    github_run_id = os.environ.get("INPUT_GITHUB_RUN_ID")
    try:
        assert github_run_id not in (None, '')
    except:
        output = "The input github run id is not set"
        print(f"Error: {output}")
        sys.exit(-1)

    github_token = os.environ.get("INPUT_GITHUB_TOKEN")
    print(github_token)
    sys.exit(-1)
    try:
        assert github_token not in (None, '')
    except:
        output = "The input github token is not set"
        print(f"Error: {output}")
        sys.exit(-1)

    github_org = os.environ.get("INPUT_GITHUB_ORG")
    try:
        assert github_org not in (None, '')
    except:
        output = "The input github org is not set"
        print(f"Error: {output}")
        sys.exit(-1)

    logs_url = f"https://api.github.com/repos/{github_org}/{github_repo}/actions/runs/{github_run_id}/logs"
    metadata_url = f"https://api.github.com/repos/{github_org}/{github_repo}/actions/runs/{github_run_id}"

    try:
        r = requests.get(metadata_url, stream=True, headers={
            "Authorization": f"token {github_token}"
        })
        metadata = json.loads(r.content)
        metadata.pop('repository')
        metadata.pop('head_repository')
        metadata = {
            "metadata_" + k: v for k,v in metadata.items()
        }
    except Exception as exc:
        output = "Failed to get run metadata" + str(exc)
        print(f"Error: {output}")
        print(f"::set-output name=result::{output}")
        sys.exit(-1)

    elastic_logger = logging.getLogger("elastic")
    try:
        s = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[404])
        s.mount('https://', HTTPAdapter(max_retries=retries))
        r = s.get(logs_url, stream=True, headers={
            "Authorization": f"token {github_token}"
        })
        if not r.ok:
            output = "Failed to download logs"
            print(f"Error: {output}")
            print(f"::set-output name=result::{output}")
            sys.exit(-1)

        z = zipfile.ZipFile(io.BytesIO(r.content))
        for log_file in z.namelist():
            if len(log_file.split("/")) != 2:
                continue
            job_name, step_name = log_file.split("/")
            with z.open(log_file) as f:
                for log in f:
                    # log is bytes, decode it to str
                    log_str = log.decode()
                    # log it to elastic
                    elastic_logger.info(log_str, extra={
                        "job": job_name,
                        "step": step_name,
                        "repo": github_repo,
                        "run_id": github_run_id,
                        **metadata
                    })

    except requests.exceptions.HTTPError as errh:
        output = "GITHUB API Http Error:" + str(errh)
        print(f"Error: {output}")
        print(f"::set-output name=result::{output}")
        sys.exit(-1)
    except requests.exceptions.ConnectionError as errc:
        output = "GITHUB API Error Connecting:" + str(errc)
        print(f"Error: {output}")
        print(f"::set-output name=result::{output}")
        sys.exit(-1)
    except requests.exceptions.Timeout as errt:
        output = "Timeout Error:" + str(errt)
        print(f"Error: {output}")
        print(f"::set-output name=result::{output}")
        sys.exit(-1)
    except requests.exceptions.RequestException as err:
        output = "GITHUB API Non catched error connecting:" + str(err)
        print(f"Error: {output}")
        print(f"::set-output name=result::{output}")
        sys.exit(-1)


def keyboard_interrupt_bug(signal, frame):
    print('keyboard interrupt')
    pass


signal.signal(signal.SIGINT, keyboard_interrupt_bug)


if __name__ == "__main__":
    main()