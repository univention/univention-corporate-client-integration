#!/usr/bin/python2.6
#
# Copyright 2012-2014 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import notifier

from univention.management.console.modules import Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer

import univention.admin.modules as udm_modules
import univention.admin.uldap as udm_uldap
udm_modules.update()

from univention.lib.i18n import Translation

_ = Translation( 'ucc-umc-setup' ).translate

class Instance(Base):
	@simple_response
	def info_networks(self):
		lo, po = udm_uldap.getMachineConnection()
		networks = udm_modules.lookup('networks/network', None, lo, base=ucr['ldap/base'], scope='sub')
		result = []
		for inet in networks:
			ilabel = '{name} ({network})'.format(**inet.info)
			result.append({
				'id': inet.dn,
				'label': ilabel
			})
		return result

	@simple_response
	def info_gateway(self):
		return ucr.get('gateway')
