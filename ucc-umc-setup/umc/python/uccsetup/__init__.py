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
import univention.admin.objects as udm_objects

from univention.lib.i18n import Translation

import util

_ = Translation( 'ucc-umc-setup' ).translate


class Instance(Base):
	def init(self):
		util.set_credentials(self._user_dn, self._password)

	@simple_response
	def info_networks(self):
		ldap_connection = util.get_ldap_connection()
		networks = udm_modules.lookup('networks/network', None, ldap_connection, base=ucr['ldap/base'], scope='sub')
		result = []
		for inet in networks:
			ilabel = '{name} ({network})'.format(**inet.info)
			result.append({
				'id': inet.dn,
				'label': ilabel
			})
		return result

	@simple_response
	def info_ucc_images(self):
		ldap_connection = util.get_ldap_connection()
		images = udm_modules.lookup('settings/ucc_image', None, ldap_connection, base=ucr['ldap/base'], scope='sub')
		result = []
		for iimg in images:
			result.append({
				'id': iimg.dn,
				'label': iimg['name'],
			})
		return result

	@simple_response
	def info(self):
		ldap_connection = util.get_ldap_connection()
		dhcp_routing_obj = util.get_dhcp_routing_policy(ldap_connection)
		ucr_policy_obj = udm_objects.get(udm_modules.get('policies/registry'), None, ldap_connection, None, util.UCR_VARIABLE_POLICY_DN)
		return {
			'gateway': ucr.get('gateway'),
			'dhcp_routing_policy': dhcp_routing_obj and dhcp_routing_obj.dn,
			'ucr_policy_exists': ucr_policy_obj.exists(),
			#TODO: return images that already exist
		}

	@simple_response
	def upload_deb(self):
		# TODO: handle upload of .deb package for Xen Retriever
		pass

	@simple_response
	def apply(self, gateway=None, rdp={}, citrix={}, thinclient=False, fatclient=False, downloadThinClientImage=False, downloadFatClientImage=False, network={}, browser={}, defaultSession=None):
		ldap_connection = util.get_ldap_connection()

		# create network obj and make sure that the network obj is linked to the DHCP service
		if network:
			if network.get('existingDN'):
				util.set_dhcp_service_for_network(network.existingDN, ldap_connection)
			else:
				#TODO: error handling
				util.set_network(network.get('address'), network.get('mask'), network.get('firstIP'), network.get('lastIP'), ldap_connection)

		# DHCP routing policy for gateway
		dhcp_routing_obj = util.get_dhcp_routing_policy(ldap_connection)
		if not dhcp_routing_obj and gateway:
			util.set_dhcp_routing(gateway, ldap_connection)

		ucr_variables = {}
		thinclient_ucr_variables = {}
		fatclient_ucr_variables = {}
		if browser:
			# web browser access
			ucr_variables['firefox/startsite'] = browser.get('url', '')
			# default session (might be overwritten by RDP or Citrix)
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'firefox'

		if rdp:
			# RDP terminal server + domain name
			util.set_rdp_values(rdp.get('domain', ''), rdp.get('host', ''), ldap_connection)
			# RDP configuration -> usb and sound
			ucr_variables['rdp/redirectdisk'] = util.bool2str(rdp.get('usb'))
			ucr_variables['rdp/disable-sound'] = util.bool2str(not rdp.get('sound'))
			# default session (might be overwritten by Citrix)
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'RDP'

		if citrix:
			# Citrix configuration
			ucr_variables['citrix/webinterface'] = citrix.get('url', '')
			ucr_variables['citrix/accepteula'] = 'true'
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'XenApp'
			if citrix.get('autoLogin'):
				thinclient_ucr_variables['lightdm/autologin/session'] = 'XenApp'
				thinclient_ucr_variables['lightdm/autologin'] = 'true'

			#TODO: Xitrix deb integration -> https://forge.univention.org/bugzilla/show_bug.cgi?id=34452#c2

		# save UCR variables as policy
		util.set_ucr_policy_variables(ucr_variables, thinclient_ucr_variables, fatclient_ucr_variables, ldap_connection)
		return True

