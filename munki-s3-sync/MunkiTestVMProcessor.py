#!/usr/local/autopkg/python
#
# Copyright 2026 Markus Stapel
"""autopkg processor to run a VM test script and report results"""

import os.path
import plistlib
import subprocess
from autopkglib import Processor, ProcessorError, get_pref

__all__ = ["MunkiTestVMProcessor"]

class MunkiTestVMProcessor(Processor):
    description = "Triggers VM test script and provides a summary report."

    input_variables = {
        "test_script_path": {
            "required": True,
            "description": "Full path to test_packages.py.",
        },
        "force_run": {
            "required": False,
            "default": "false",
            "description": "If true, run even without repo changes.",
        },
    }
    output_variables = {
        "testvm_summary_result": {
            "description": "Summary of the VM test run."
        }
    }

    def main(self):
        cache_dir = get_pref("CACHE_DIR") or os.path.expanduser("~/Library/AutoPkg/Cache")
        current_run_results_plist = os.path.join(cache_dir, "autopkg_results.plist")
        
        try:
            with open(current_run_results_plist, "rb") as f:
                run_results = plistlib.load(f)
        except:
            run_results = []

        repo_changed = False
        for result in run_results:
            for item in result:
                if "Output" in item and item["Output"].get("munki_repo_changed", False):
                    repo_changed = True
                    break

        force = str(self.env.get("force_run")).lower() == "true"
        test_script_path = self.env.get("test_script_path")

        if not repo_changed and not force:
            self.output("No changes detected. Skipping VM tests.")
        else:
            self.output(f"Triggering VM test: {test_script_path}")
            try:
                # Wir fangen stdout UND stderr ab, um Fehler im Log zu sehen
                proc = subprocess.Popen(
                    [test_script_path], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True
                )
                
                full_output = []
                for line in proc.stdout:
                    clean_line = line.strip()
                    full_output.append(clean_line)
                    self.output(f"VM-TEST: {clean_line}")
                
                proc.wait()
                
                # Erstellt die Zusammenfassung für den AutoPkg-Report
                self.env["testvm_summary_result"] = {
                    "summary_text": "The following VM test activities occurred:",
                    "report_variables": {
                        "script": test_script_path,
                        "status": "Success" if proc.returncode == 0 else "FAILED",
                        "exit_code": str(proc.returncode),
                        "last_line": full_output[-1] if full_output else "No output"
                    }
                }

                if proc.returncode != 0:
                    raise ProcessorError(f"VM Test script failed with code {proc.returncode}. Check logs above.")

            except Exception as e:
                raise ProcessorError(f"Processor failed: {e}")

if __name__ == "__main__":
    PROCESSOR = MunkiTestVMProcessor()
    PROCESSOR.execute_shell()
