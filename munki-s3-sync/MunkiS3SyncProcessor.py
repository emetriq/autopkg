#!/usr/bin/python
#
# Copyright 2021 Markus Stapel
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
"""autopkg processor to run munki-s3-sync on a Munki repo"""

import os.path
import plistlib
import subprocess

from autopkglib import Processor, ProcessorError, get_pref

__all__ = ["MunkiS3SyncProcessor"]


class MunkiS3SyncProcessor(Processor):
    """Runs munki-s3-sync on a munki repo"""

    input_variables = {
    #    "MUNKI_REPO": {"required": True, "description": "Munki repo URL."},
    #    "MUNKI_REPO_PLUGIN": {
    #        "required": False,
    #        "description": "Name of a Munki repo plugin. Defaults to FileRepo",
    #    },
    #    "force_rebuild": {
    #        "required": False,
    #        "description": (
    #            "If not false or empty or undefined, force a makecatalogs run."
    #        ),
    #    },
    }
    output_variables = {
        "munkis3sync_resultcode": {
            "description": "Result code from the munki-s3-sync operation."
        },
        "munkis3sync_stderr": {
            "description": "Error output (if any) from munki-s3-sync."
        },
    }

    description = __doc__

    def main(self):
        """Sync Munki catalogs to S3"""

        cache_dir = get_pref("CACHE_DIR") or os.path.expanduser(
            "~/Library/AutoPkg/Cache"
        )
        current_run_results_plist = os.path.join(cache_dir, "autopkg_results.plist")
        try:
            run_results = plistlib.readPlist(current_run_results_plist)
        except (IOError, OSError):
            run_results = []

        something_imported = False
        # run_results is an array of autopackager.results,
        # which is itself an array.
        # look through all the results for evidence that
        # something was imported
        # this could probably be done as an array comprehension
        # but might be harder to grasp...
        for result in run_results:
            for item in result:
                if item.get("Processor") == "MunkiImporter":
                    #if item["Output"].get("pkginfo_repo_path"):
                    something_imported = True
                    break
	#if not something_imported and not self.env.get("force_rebuild"):
        if not something_imported:
            self.output("No need to sync catalogs.")
            self.env["munkis3sync_resultcode"] = 0
            self.env["munkis3sync_stderr"] = ""
        else:
            # Generate arguments for munki-s3-sync.
            args = ["/usr/local/bin/munki-s3-sync.sh"]
            
            #if self.env["MUNKI_REPO"].startswith("/"):
            #    # looks a file path instead of a URL
            #    args.append(self.env["MUNKI_REPO"])
            #else:
            #    args.extend(["--repo-url", self.env["MUNKI_REPO"]])

            #if self.env.get("MUNKI_REPO_PLUGIN"):
            #    args.extend(["--plugin", self.env["MUNKI_REPO_PLUGIN"]])

            # Call munki-s3-sync.
            try:
                proc = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                (_, err_out) = proc.communicate()
            except OSError as err:
                raise ProcessorError(
                    "munki-s3-sync execution failed with error code %d: %s"
                    % (err.errno, err.strerror)
                )

            self.env["munkis3sync_resultcode"] = proc.returncode
            self.env["munkis3sync_stderr"] = err_out.decode("utf-8")
            if proc.returncode != 0:
                error_text = "munki-s3-sync failed: \n" + self.env["munkis3sync_stderr"]
                raise ProcessorError(error_text)
            else:
                self.output("Munki catalogs synced!")


if __name__ == "__main__":
    PROCESSOR = MunkiS3SyncProcessor()
    PROCESSOR.execute_shell()
