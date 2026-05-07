#!/usr/local/autopkg/python
"""autopkg processor to run munki-s3-sync on a Munki repo"""

import os.path
import plistlib
import subprocess
from autopkglib import Processor, ProcessorError, get_pref

__all__ = ["MunkiS3SyncProcessor"]

class MunkiS3SyncProcessor(Processor):
    description = "Runs munki-s3-sync.sh if repo changed or force_run is True."

    input_variables = {
        "s3_sync_script": {
            "required": False,
            "default": "/usr/local/bin/munki-s3-sync.sh",
            "description": "Path to the munki-s3-sync shell script.",
        },
        "force_run": {
            "required": False,
            "default": False,
            "description": "If True, the sync will run even if no changes were detected.",
        },
    }
    output_variables = {
        "munkis3sync_resultcode": {"description": "Result code from the operation."}
    }

    def main(self):
        cache_dir = get_pref("CACHE_DIR") or os.path.expanduser("~/Library/AutoPkg/Cache")
        current_run_results_plist = os.path.join(cache_dir, "autopkg_results.plist")
        
        try:
            with open(current_run_results_plist, "rb") as f:
                run_results = plistlib.load(f)
        except (IOError, OSError):
            run_results = []

        repo_changed = False
        for result in run_results:
            for item in result:
                if "Output" in item and item["Output"].get("munki_repo_changed", False):
                    repo_changed = True
                    break

        # Prüfung auf force_run (Eingabe kann String oder Boolean sein)
        force = str(self.env.get("force_run")).lower() == "true"
        s3_script = self.env.get("s3_sync_script")

        if not repo_changed and not force:
            self.output("No changes detected and force_run is False. Skipping S3 sync.")
        else:
            if force:
                self.output("Force run enabled. Proceeding with S3 sync...")
            
            try:
                proc = subprocess.Popen([s3_script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    self.output(f"S3-SYNC: {line.strip()}")
                proc.wait()
                self.env["munkis3sync_resultcode"] = proc.returncode
                if proc.returncode != 0:
                    raise ProcessorError(f"S3 sync failed (Code {proc.returncode})")
            except OSError as err:
                raise ProcessorError(f"Execution failed: {err.strerror}")

if __name__ == "__main__":
    PROCESSOR = MunkiS3SyncProcessor()
    PROCESSOR.execute_shell()
