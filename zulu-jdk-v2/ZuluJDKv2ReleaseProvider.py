from autopkglib import Processor, ProcessorError, URLGetter
import re

apiBaseUrl = "https://api.azul.com/zulu/download/community/v1.0/bundles/latest/binary"


class ZuluJDKv2ReleaseProvider(URLGetter):
    input_variables = {
        "JAVA_VERSION": {
            "required": True,
            "description": "A valid major version like 8, 11 or 17.",
        },
        "JAVA_ARCH": {
            "required": True,
            "description": "A valid architecture like arm or x86.",
        }
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Zulu OpenJDK for given version and architecture."
        },
        "JDK_CHECK": {
            "description": "Install Check Script."
        },
        "JDK_VERSION": {
            "description": "Version of the latest Zulu OpenJDK for given version and architecture."
        },
        "MUNKI_ARCHITECTURE": {
            "description": "Architecture needed by munki for this release: arm64 or x86_64."
        }
    }

    def main(self):
        # Azul has an API, which gives us the latest release
        # for given version and architecture
        apiCall = "%s/?java_version=%s&os=macos&arch=%s&ext=dmg&release_status=ga&package=jdk" % (
            apiBaseUrl, self.env["JAVA_VERSION"], self.env["JAVA_ARCH"]
        )
        self.output("Get latest Version from api with: %s" % apiCall)
        curl_cmd = [self.curl_binary()]
        curl_cmd.append(apiCall)
        redirectRequest = self.download_with_curl(curl_cmd, text=True)

        # The URLGetter class doesn't returns the header, so we
        # have to find out the redirect URL with an regular
        # expression instead of just reading the Location header
        match = re.search(r'href=[\'"]?([^\'" >]+)', redirectRequest)

        if match:
            downloadUrl = match.group(1)
            # If there is a match, first split the filename
            # from the base path
            (baseUrl, jdkFilename) = downloadUrl.rsplit("/", 1)

            # Then split the filename into
            # azul version  - something like zulu8.64.0.19-ca-fx
            # jdk version   - something like 11.0.7
            # and the type  - something like macosx_aarch64.dmg
            (azulVersion, jdkVersionTemp, binaryTyp) = jdkFilename.rsplit("-", 2)
            jdkVersion = jdkVersionTemp[3:]
            jdkCheckVersion = jdkVersion
            (jdkMajor, jdkMinor, jdkPatch) = jdkVersion.split(".", 2)

            # Versionnumbering on JDK8 is a bit different
            # so we're rewriting it
            if self.env["JAVA_VERSION"] == "8":
                jdkVersion = "1.8.%s" % jdkPatch
                jdkCheckVersion = "1.8.0.%s" % jdkPatch
                jdkMajor = "1.8"

            # Create installcheck_script
            jdkCheckScript = """#!/bin/bash

# Put in the main and the new version number
MAINVERSION=\"%s\"
NEWVERSION=\"%s\"

# function to compare versions
function version { echo \"$@\" | awk -F. '{ printf(\"%%d%%03d%%03d%%03d\\n\", $1,$2,$3,$4); }'; }

# Check if a Java of this mainversion is installed
/usr/libexec/java_home -F -v ${MAINVERSION}
if [ \"$?\" -ne 0 ]; then
  echo \"No Java ${MAINVERSION} installed.\"
  exit 0
fi

JAVAHOME=`/usr/libexec/java_home -v ${MAINVERSION}`
INSTALLEDVERSION=`${JAVAHOME}/bin/java -version 2>&1 | head -n 1 | awk -F '\"' '{print $2}' |tr '_' '.'`

echo \"New Java ${MAINVERSION} Version       is ${NEWVERSION}\"
echo \"Installed Java ${MAINVERSION} Version is ${INSTALLEDVERSION}\"

if [ \"$(version \"${NEWVERSION}\")\" -gt \"$(version \"${INSTALLEDVERSION}\")\" ]; then
  echo \"Newer version avaible.\"
  exit 0
else
  echo \"Installed Version is up-to-date.\"
  exit 1
fi

echo \"Not sure which version is installed and if it's newer - so just install it again... :-(\"
exit 0
""" % (jdkMajor, jdkCheckVersion)
            # Output what was found
            self.output(" Latest Open JDK %s for %s" % (
                self.env["JAVA_VERSION"], self.env["JAVA_ARCH"]
            ))
            self.output(" Version     : %s" % jdkVersion)
            self.output(" Zulu Version: %s" % azulVersion)
            self.output(" URL         : %s" % downloadUrl)

            # Write the needed output to environment
            self.env["url"] = downloadUrl
            self.env["JDK_VERSION"] = jdkVersion
            self.env["JDK_CHECK"] = jdkCheckScript
            if self.env["JAVA_ARCH"] == "arm":
                self.env["MUNKI_ARCHITECTURE"] = "arm64"
            elif self.env["JAVA_ARCH"] == "x86":
                self.env["MUNKI_ARCHITECTURE"] = "x86_64"
        else:
            # Something gone wrong, so the recipe will crash now
            self.output("No redirect found for latest Zulu JDK %s for arch %s" % (
                self.env["JAVA_VERSION"], self.env["JAVA_ARCH"]
            ))


if __name__ == "__main__":
    PROCESSOR = ZuluJDKv2ReleaseProvider()
    PROCESSOR.execute_shell()
