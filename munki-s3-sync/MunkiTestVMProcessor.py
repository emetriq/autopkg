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
        # Scanne Ergebnisse nach MunkiImporter Aktivität
        for result in run_results:
            for item in result:
                if item.get("Processor") == "MunkiImporter":
                    something_imported = True
                    break
        
        if not something_imported:
            self.output("No new imports detected. Skipping VM tests.")
            self.env["testvm_resultcode"] = 0
        else:
            self.output(f"New imports found! Triggering VM test: {self.test_script_path}")
            
            args = [self.test_script_path]

            try:
                # Wir führen das Script aus und streamen den Output in die AutoPkg Konsole
                proc = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                
                # Live-Output in die AutoPkg Konsole schreiben
                for line in proc.stdout:
                    self.output(f"VM-TEST: {line.strip()}")
                
                proc.wait()
                
            except OSError as err:
                raise ProcessorError(
                    "Execution of test script failed: %s" % err.strerror
                )

            self.env["testvm_resultcode"] = proc.returncode
            
            if proc.returncode != 0:
                raise ProcessorError(f"VM Test script failed with return code {proc.returncode}")
            else:
                self.output("VM Test run completed successfully!")

if __name__ == "__main__":
    PROCESSOR = MunkiTestVMProcessor()
    PROCESSOR.execute_shell()
