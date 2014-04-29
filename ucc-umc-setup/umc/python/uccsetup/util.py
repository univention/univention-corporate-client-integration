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

from contextlib import contextmanager
import ipaddr

from univention.management.console.config import ucr
from univention.management.console.log import MODULE

import univention.admin.modules as udm_modules
import univention.admin.uldap as udm_uldap
import univention.admin.objects as udm_objects
udm_modules.update()

UCC_NETWORK_DN = 'cn=ucc-network,cn=networks,%s' % ucr['ldap/base']
UCC_USER_SESSION_POLICY_DN = 'cn=ucc-usersession,cn=policies,%s' % ucr['ldap/base']
UCR_VARIABLE_POLICY_DN = 'cn=ucc-common-settings,cn=config-registry,cn=policies,%s' % ucr['ldap/base']
UCR_VARIABLE_POLICY_THINCLIENTS_DN = 'cn=ucc-thinclient-settings,cn=config-registry,cn=policies,%s' % ucr['ldap/base']
UCR_VARIABLE_POLICY_FATCLIENTS_DN = 'cn=ucc-desktop-settings,cn=config-registry,cn=policies,%s' % ucr['ldap/base']
DHCP_ROUTING_POLICY_DN = 'cn=ucc-dhcp-gateway,cn=routing,cn=dhcp,cn=policies,%s' % ucr['ldap/base']

_user_dn = None
_password = None
def set_credentials( dn, passwd ):
	global _user_dn, _password
	_user_dn = dn
	_password = passwd
	MODULE.info('Saved LDAP DN for user %s' % _user_dn)

def get_ldap_connection():
	MODULE.info('Open LDAP connection for user %s' % _user_dn )
	return udm_uldap.access(base=ucr.get('ldap/base'), binddn=_user_dn, bindpw=_password, follow_referral=True)

def bool2str(b):
	if b:
		return 'true'
	return 'false'

def _get_dhcp_service_obj(ldap_connection):
	result = udm_modules.lookup('dhcp/service', None, ldap_connection, scope='sub', base='cn=dhcp,%s' % ucr['ldap/base'])
	if not result:
		#TODO: error handling
		MODULE.error('ERROR: Failed to open UDM DHCP service object, maybe the DHCP server component is not installed?')
		return None

	return result[0]

def _get_forward_zone(ldap_connection):
	result = udm_modules.lookup('dns/forward_zone', None, ldap_connection, scope='sub', base='cn=dns,%s' % ucr['ldap/base'])
	if not result:
		#TODO: error handling
		MODULE.error('ERROR: Failed to find a DNS forward zone?')
		return None

	return result[0]

def _get_reverse_zone(address, mask, ldap_connection):
	dns_container_dn = 'cn=dns,%s' % ucr['ldap/base']
	network = ipaddr.IPNetwork('%s/%s' % (address, mask))
	subnet = '.'.join(str(network.network).split('.')[:network.prefixlen / 8])
	result = udm_modules.lookup('dns/reverse_zone', None, ldap_connection, filter='subnet=%s' % subnet, scope='sub', base=dns_container_dn)
	if result:
		# reverse zone already exists
		return result[0]

	# create a new reverse zone
	zone_obj = udm_objects.get(udm_modules.get('dns/reverse_zone'), None, ldap_connection, udm_uldap.position(dns_container_dn))
	zone_obj.open()
	zone_obj['subnet'] = subnet
	zone_obj['nameserver'] = ucr['ldap/master']
	zone_obj.create()
	return zone_obj

def _get_default_network(ldap_connection):
		network_dn = 'cn=default,cn=networks,%s' % ucr['ldap/base']
		network_obj = udm_objects.get(udm_modules.get('networks/network'), None, ldap_connection, None, network_dn)
		network_obj.open()
		return network_obj

def set_network(address, mask, first_ip, last_ip, ldap_connection):
	# open network object
	network_obj = udm_objects.get(udm_modules.get('networks/network'), None, ldap_connection, None, UCC_NETWORK_DN)

	if network_obj.exists():
		# remove network object if already existing
		network_obj.remove()
		network_obj = udm_objects.get(udm_modules.get('networks/network'), None, ldap_connection, None, UCC_NETWORK_DN)

	# create network
	name = udm_uldap.explodeDn(UCC_NETWORK_DN, True)[0]
	path = UCC_NETWORK_DN.split(',', 1)[1]
	network_obj = udm_objects.get(udm_modules.get('networks/network'), None, ldap_connection, udm_uldap.position(path))
	network_obj.open()

	# set network values
	#TODO: error handling
	network_obj['name'] = name
	network_obj['network'] = address
	network_obj['netmask'] = mask
	if first_ip and last_ip:
		network_obj['ipRange'] = [[first_ip, last_ip]]

	# register the DHCP service at the network
	dhcp_service_obj = _get_dhcp_service_obj(ldap_connection)
	if dhcp_service_obj:
		network_obj['dhcpEntryZone'] = dhcp_service_obj.dn

	# register DNS forward/reverse zone
	if not network_obj.get('dnsEntryZoneForward'):
		forward_zone_obj = _get_forward_zone(ldap_connection)
		if forward_zone_obj:
			network_obj['dnsEntryZoneForward'] = forward_zone_obj.dn
	if not network_obj['dnsEntryZoneReverse']:
		reverse_zone_obj = _get_reverse_zone(address, mask, ldap_connection)
		if reverse_zone_obj:
			network_obj['dnsEntryZoneReverse'] = reverse_zone_obj.dn

	# save changes
	print '# network:', network_obj.info
	network_obj.create()

def set_dhcp_service_for_network(network_dn, ldap_connection):
	network_obj = udm_objects.get(udm_modules.get('networks/network'), None, ldap_connection, None, network_dn)
	network_obj.open()
	if 'dhcpEntryZone' in network_obj and network_obj['dhcpEntryZone']:
		return

	# register the DHCP service at the specified network
	dhcp_service_obj = _get_dhcp_service_obj(ldap_connection)
	if dhcp_service_obj:
		network_obj['dhcpEntryZone'] = dhcp_service_obj.dn
		network_obj.modify()

def _get_policy_object(policy_dns, module_name, ldap_connection):
	for idn in policy_dns:
		attrs = ldap_connection.lo.get(idn)
		matching_modules = udm_modules.identify(idn, attrs, module_base = 'policies/')
		policy_modules = [ imodule for imodule in matching_modules if imodule.module == module_name ]
		if policy_modules:
			return udm_objects.get(policy_modules[0], None, ldap_connection, None, idn, attributes = attrs)
	return None

@contextmanager
def _set_policy(container_dn, policy_type, policy_dn, ldap_connection):
	# open policy object at the given container
	container_obj = udm_objects.get(udm_modules.get('container/cn'), None, ldap_connection, None, container_dn)
	container_obj.open()
	policy_obj = _get_policy_object(container_obj.policies, policy_type, ldap_connection)
	if policy_obj:
		# a policy object is already associated with the container
		policy_obj.open()
	else:
		# try to open the policy with the given DN
		policy_obj = udm_objects.get(udm_modules.get(policy_type), None, ldap_connection, None, policy_dn)
		if not policy_obj.exists():
			# create policy
			name = udm_uldap.explodeDn(policy_dn, True)[0]
			path = policy_dn.split(',', 1)[1]
			policy_obj = udm_objects.get(udm_modules.get(policy_type), None, ldap_connection, udm_uldap.position(path))
			policy_obj.open()
			policy_obj['name'] = name

	yield policy_obj

	# make sure that the policy is set at the container
	if not policy_obj.dn in container_obj.policies:
		container_obj.policies.append(policy_obj.dn)
		container_obj.modify()

	# save changes policy obj
	if policy_obj.exists():
		policy_obj.modify()
	else:
		policy_obj.create()

def set_ucr_policy_variables(common_variables, thinclient_variables, fatclient_variables, ldap_connection):
	computers_container_dn = 'cn=computers,%s' % ucr['ldap/base']
	thinclients_container_dn = 'cn=ucc-thinclients,cn=computers,%s' % ucr['ldap/base']
	fatclients_container_dn = 'cn=ucc-desktops,cn=computers,%s' % ucr['ldap/base']
	items = [
		(computers_container_dn, common_variables, UCR_VARIABLE_POLICY_DN),
		(thinclients_container_dn, thinclient_variables, UCR_VARIABLE_POLICY_THINCLIENTS_DN),
		(fatclients_container_dn, fatclient_variables, UCR_VARIABLE_POLICY_FATCLIENTS_DN),
	]
	for container_dn, variables, policy_dn in items:
		with _set_policy(container_dn, 'policies/registry', policy_dn, ldap_connection) as ucr_policy:
			variable_dict = dict(ucr_policy.get('registry', []))
			variable_dict.update(variables)
			ucr_policy['registry'] = variable_dict.items()

def get_dhcp_routing_policy(ldap_connection):
	dhcp_container_dn = 'cn=dhcp,%s' % ucr['ldap/base']
	dhcp_container_obj = udm_objects.get(udm_modules.get('container/cn'), None, ldap_connection, None, dhcp_container_dn)
	dhcp_container_obj.open()
	return _get_policy_object(dhcp_container_obj.policies, 'policies/dhcp_routing', ldap_connection)

def set_dhcp_routing(gateway, ldap_connection):
	dhcp_container_dn = 'cn=dhcp,%s' % ucr['ldap/base']
	with _set_policy(dhcp_container_dn, 'policies/dhcp_routing', DHCP_ROUTING_POLICY_DN, ldap_connection) as dhcp_policy:
		if gateway not in dhcp_policy.get('routers', []):
			dhcp_policy['routers'].append(gateway)

def set_rdp_values(domain, terminal_server, ldap_connection):
	computers_container_dn = 'cn=computers,%s' % ucr['ldap/base']
	with _set_policy(computers_container_dn, 'policies/ucc_user', UCC_USER_SESSION_POLICY_DN, ldap_connection) as users_session_policy:
		users_session_policy['windowsDomain'] = domain
		users_session_policy['windowsTerminalserver'] = terminal_server


