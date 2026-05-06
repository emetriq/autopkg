#!/usr/local/autopkg/python
#
# Copyright 2026 Markus Stapel
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""autopkg processor to run munki-s3-sync on a Munki repo if it has changed"""

import os.path
import plistlib
import subprocess

from autopkglib import Processor, ProcessorError, get_pref

__all__ = ["MunkiS3SyncProcessor"]

class MunkiS3SyncProcessor(Processor):
    """Runs munki-s3-sync.sh on a munki repo only if changes were detected."""

    input_variables = {
        "s3_sync_script": {
            "required": False,
            "default": "/usr/local/bin/munki-s3-sync.sh",
            "description": "Path to the munki-s3-sync shell script.",
        },
    }
    output_variables = {
        "munkis3sync_resultcode": {
            "description": "Result code from the munki-s3-sync operation."
        }
    }

    description = __doc__

    def main(self):
        """Sync Munki catalogs to S3 if repo changed"""

        # Pfad zur Ergebnisliste des aktuellen Laufs
        cache_dir = get_pref("CACHE_DIR") or os.path.expanduser(
            "~/Library/AutoPkg/Cache"
        )
        current_run_results_plist = os.path.join(cache_dir, "autopkg_results.plist")
        
        try:
            with open(current_run_results_plist, "rb") as f:
                run_results = plistlib.load(f)
        except (IOError, OSError):
            run_results = []

        # Prüfung auf Änderungen (Standard-Logik von Greg Neagle)
        repo_changed = False
        for result in run_results:
            for item in result:
                if "Output" in item and item["Output"].get("munki_repo_changed", False):
                    repo_changed = True
                    break

        s3_script = self.env.get("s3_sync_script")

        if not repo_changed:
            self.output("No changes detected in Munki repo. Skipping S3 sync.")
            self.env["munkis3sync_resultcode"] = 0
        else:
            self.output(f"Repo changed! Running S3 sync script: {s3_script}")
            
            try:
                # Script ausführen
                proc = subprocess.Popen(
                    [s3_script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                
                # Output für das AutoPkgr Log erfassen
                for line in proc.stdout:
                    self.output(f"S3-SYNC: {line.strip()}")
                
                proc.wait()
                self.env["munkis3sync_resultcode"] = proc.returncode
                
                if proc.returncode != 0:
                    raise ProcessorError(f"S3 sync script failed with return code {proc.returncode}")
                
                self.output("S3 sync completed successfully!")

            except OSError as err:
                raise ProcessorError(f"Execution of S3 sync script failed: {err.strerror}")

if __name__ == "__main__":
    PROCESSOR = MunkiS3SyncProcessor()
    PROCESSOR.execute_shell()
