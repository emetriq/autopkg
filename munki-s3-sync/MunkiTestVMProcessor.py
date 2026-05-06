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
"""autopkg processor to run a VM test script if the Munki repo has changed"""

import os.path
import plistlib
import subprocess

from autopkglib import Processor, ProcessorError, get_pref

__all__ = ["MunkiTestVMProcessor"]

class MunkiTestVMProcessor(Processor):
    """Runs a VM test script if a previous processor signaled a repo change."""

    input_variables = {
        "test_script_path": {
            "required": True,
            "description": "Full path to the Python test script (test_packages.py).",
        },
    }
    output_variables = {
        "testvm_resultcode": {
            "description": "Result code from the VM test script."
        },
    }

    description = __doc__

    def main(self):
        cache_dir = get_pref("CACHE_DIR") or os.path.expanduser(
            "~/Library/AutoPkg/Cache"
        )
        current_run_results_plist = os.path.join(cache_dir, "autopkg_results.plist")
        
        try:
            with open(current_run_results_plist, "rb") as f:
                run_results = plistlib.load(f)
        except (IOError, OSError):
            run_results = []

        # Logik analog zu MakeCatalogsProcessor
        repo_changed = False
        for result in run_results:
            for item in result:
                if "Output" in item and item["Output"].get("munki_repo_changed", False):
                    repo_changed = True
                    break
        
        test_script_path = self.env.get("test_script_path")

        if not repo_changed:
            self.output("No changes detected in Munki repo. Skipping VM tests.")
            self.env["testvm_resultcode"] = 0
        else:
            if not test_script_path:
                raise ProcessorError("Input variable 'test_script_path' is missing!")

            self.output(f"Repo changed! Triggering VM test: {test_script_path}")
            
            try:
                # Script ausführen und Output streamen
                proc = subprocess.Popen(
                    [test_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                
                for line in proc.stdout:
                    self.output(f"VM-TEST: {line.strip()}")
                
                proc.wait()
                self.env["testvm_resultcode"] = proc.returncode
                
                if proc.returncode != 0:
                    raise ProcessorError(f"VM Test script failed with return code {proc.returncode}")
                
                self.output("VM Test run completed successfully!")

            except OSError as err:
                raise ProcessorError(f"Execution of test script failed: {err.strerror}")

if __name__ == "__main__":
    PROCESSOR = MunkiTestVMProcessor()
    PROCESSOR.execute_shell()
