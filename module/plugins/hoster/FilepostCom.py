# -*- coding: utf-8 -*-
"""
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License,
    or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, see <http://www.gnu.org/licenses/>.

    @author: zoidberg
"""

import re
from module.plugins.Hoster import Hoster
from module.network.RequestFactory import getURL
from module.plugins.ReCaptcha import ReCaptcha
from json import loads as json_loads
from time import time

def getInfo(urls):
    result = []

    for url in urls:
        html = getURL(url, decode=True)
        if re.search(FilepostCom.FILE_OFFLINE_PATTERN, html):
            # File offline
            result.append((url, 0, 1, url))
        else:
            # Get file info
            name, size = url, 0

            found = re.search(FilepostCom.FILE_INFO_PATTERN, html)
            if found is not None:
                name, size, units = found.groups()
                size = float(size) * 1024 ** {'KB': 1, 'MB': 2, 'GB': 3}[units]
                result.append((name, size, 2, url))
    yield result

class FilepostCom(Hoster):
    __name__ = "FilepostCom"
    __type__ = "hoster"
    __pattern__ = r"https?://(?:\www\.)?filepost\.com/files/([^/]+).*"
    __version__ = "0.1"
    __description__ = """Filepost.com plugin - free only"""
    __author_name__ = ("zoidberg")
    __author_mail__ = ("zoidberg@mujmail.cz")

    FILE_INFO_PATTERN = r'<h1>([^<]+)</h1>\s*<div class="ul">\s*<ul>\s*<li><span>Size:</span> ([0-9.]+) (KB|MB|GB)</li>'
    FILE_OFFLINE_PATTERN = r'class="error_msg_title"> Invalid or Deleted File. </div>'
    RECAPTCHA_KEY_PATTERN = r"Captcha.init\({\s*key:\s*'([^']+)'"
    FLP_TOKEN_PATTERN = r"store.set\('flp_token', '([^']+)'\);"

    def setup(self):
        self.multiDL = False

    def process(self, pyfile):
        self.html = self.load(pyfile.url)
        self.getFileInfo(pyfile)
        self.handleFree(pyfile)

    def getFileInfo(self, pyfile):
        if re.search(self.FILE_OFFLINE_PATTERN, self.html): self.offline()

        found = re.search(self.FILE_INFO_PATTERN, self.html)
        if not found: self.fail("Parse error (file info)")
        pyfile.name, size, units = found.groups()
        pyfile.size = float(size) * 1024 ** {'KB': 1, 'MB': 2, 'GB': 3}[units]

    def handleFree(self, pyfile):
        # Find token and captcha key
        file_id = re.search(self.__pattern__, pyfile.url).group(1)
        found = re.search(self.FLP_TOKEN_PATTERN, self.html)
        if not found: self.fail("Parse error (token)")
        flp_token = found.group(1)

        found = re.search(self.RECAPTCHA_KEY_PATTERN, self.html)
        if not found: self.fail("Parse error (captcha key)")
        captcha_key = found.group(1)

        url = 'https://filepost.com/files/get/'

        # Get wait time
        get_dict = {'SID' : self.req.cj.getCookie('SID'), 'JsHttpRequest' : str(int(time()*10000)) + '-xml'}
        post_dict = {'action' : 'set_download', 'download' : flp_token, 'code' : file_id}
        json_response = json_loads(self.load(url, get = get_dict, post = post_dict))
        self.logDebug(json_response)
        try:
            self.setWait(int(json_response['js']['answer']['wait_time']))
        except Exception, e:
            self.logError(e)
            self.fail("Parse error (wait time)")
        self.wait()

        # Solve recaptcha
        recaptcha = ReCaptcha(self)
        for i in range(5):
            captcha_challenge, captcha_response = recaptcha.challenge(captcha_key)
            self.logDebug("RECAPTCHA: %s : %s : %s" % (captcha_key, captcha_challenge, captcha_response))

            get_dict['JsHttpRequest'] = str(int(time()*10000)) + '-xml'
            post_dict = {'download' : flp_token, 'code' : file_id,
                "recaptcha_challenge_field" : captcha_challenge,
                "recaptcha_response_field" : captcha_response
                }

            json_response = json_loads(self.load(url, get = get_dict, post = post_dict))
            try:
                download_url = json_response['js']['answer']['link']
                self.correctCaptcha()
                break
            except:
                self.invalidCaptcha()
        else: self.fail("Invalid captcha")

        # Download
        self.download(download_url)