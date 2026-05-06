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
"""autopkg processor to run a VM test script if something was imported to Munki"""

import os.path
import plistlib
import subprocess

from autopkglib import Processor, ProcessorError, get_pref

__all__ = ["MunkiTestVMProcessor"]

class MunkiTestVMProcessor(Processor):
    """Runs a VM test script if MunkiImporter has imported something during the run."""

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
        """Check if something was imported and trigger VM test"""

        cache_dir = get_pref("CACHE_DIR") or os.path.expanduser(
            "~/Library/AutoPkg/Cache"
        )
        current_run_results_plist = os.path.join(cache_dir, "autopkg_results.plist")
        
        try:
            with open(current_run_results_plist, "rb") as f:
                run_results = plistlib.load(f)
        except (IOError, OSError):
            run_results = []

        something_imported = False
        for result in run_results:
            for item in result:
                if item.get("Processor") == "MunkiImporter":
                    something_imported = True
                    break
        
        # Zugriff auf Variable via env Dictionary (Fix für 'attribute' Error)
        test_script_path = self.env.get("test_script_path")

        if not something_imported:
            self.output("No new imports detected. Skipping VM tests.")
            self.env["testvm_resultcode"] = 0
        else:
            if not test_script_path:
                raise ProcessorError("Input variable 'test_script_path' is missing!")

            self.output(f"New imports found! Triggering VM test: {test_script_path}")
            
            try:
                # Streamt den Output des Scripts live in das AutoPkgr Log
                proc = subprocess.Popen(
                    [test_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                
                for line in proc.stdout:
                    self.output(f"VM-TEST: {line.strip()}")
                
                proc.wait()
                self.env["testvm_resultcode"] = proc.returncode
                
            except OSError as err:
                raise ProcessorError(f"Execution of test script failed: {err.strerror}")

            if proc.returncode != 0:
                raise ProcessorError(f"VM Test script failed with return code {proc.returncode}")
            else:
                self.output("VM Test run completed successfully!")

if __name__ == "__main__":
    PROCESSOR = MunkiTestVMProcessor()
    PROCESSOR.execute_shell()