#!/usr/local/autopkg/python
"""autopkg processor to run a VM test script"""

import os.path
import plistlib
import subprocess
from autopkglib import Processor, ProcessorError, get_pref

__all__ = ["MunkiTestVMProcessor"]

class MunkiTestVMProcessor(Processor):
    description = "Triggers VM test script if repo changed or force_run is True."

    input_variables = {
        "test_script_path": {
            "required": True,
            "description": "Full path to test_packages.py.",
        },
        "force_run": {
            "required": False,
            "default": False,
            "description": "If True, the test will run even if no changes were detected.",
        },
    }
    output_variables = {
        "testvm_resultcode": {"description": "Result code from the script."}
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

        force = str(self.env.get("force_run")).lower() == "true"
        test_script_path = self.env.get("test_script_path")

        if not repo_changed and not force:
            self.output("No changes detected and force_run is False. Skipping VM tests.")
        else:
            if force:
                self.output("Force run enabled. Proceeding with VM test...")
            
            try:
                proc = subprocess.Popen([test_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    self.output(f"VM-TEST: {line.strip()}")
                proc.wait()
                self.env["testvm_resultcode"] = proc.returncode
                if proc.returncode != 0:
                    raise ProcessorError(f"VM Test script failed (Code {proc.returncode})")
            except OSError as err:
                raise ProcessorError(f"Execution failed: {err.strerror}")

if __name__ == "__main__":
    PROCESSOR = MunkiTestVMProcessor()
    PROCESSOR.execute_shell()
