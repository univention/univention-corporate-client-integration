# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  UDM policy for user session configuration
#
# Copyright (C) 2010-2012 Univention GmbH
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

import sys, string
sys.path=['.']+sys.path

from univention.admin.layout import Tab, Group
import univention.admin.syntax
import univention.admin.filter
import univention.admin.handlers
import univention.admin.localization

import univention.debug

translation=univention.admin.localization.translation('univention.admin.handlers.ucc-policies')
_=translation.translate

class uccUserFixedAttributes(univention.admin.syntax.select):
	name='slavePackagesFixedAttributes'
	choices=[
		('univentionCorporateClientUserSession',_('Force this session for user logins')),
		('univentionCorporateClientUserWindowsDomain',_('Windows domain')),
		('univentionCorporateClientUserWindowsTerminalserver',_('Windows terminal server')),
		('univentionCorporateClientUserUccTerminalserver',_('UCC terminal server')),
		]

module='policies/ucc_user'
operations=['add','edit','remove','search']

policy_oc='univentionCorporateClientUserSession'
policy_apply_to=["users/user"]
policy_position_dn_prefix="cn=ucc"

childs=0
short_description=_('Policy: Univention Corporate Client user session')
policy_short_description=_('UCC user session')
long_description=''
options={
}
property_descriptions={
	'name': univention.admin.property(
			short_description=_('Name'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=1,
			may_change=0,
			identifies=1,
		),
	'session': univention.admin.property(
			short_description=_('Force this session for user logins'),
			long_description=_('This UCC session will be during login and no user selection is made'),
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'windowsDomain': univention.admin.property(
			short_description=_('Windows domain'),
			long_description=_('This windows domain will be used for RDP user logons.'),
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'windowsTerminalserver': univention.admin.property(
			short_description=_('Windows terminal server'),
			long_description=_('This windows terminal server will be used for user logon Windows terminal servers.'),
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'uccTerminalserver': univention.admin.property(
			short_description=_('UCC terminal server'),
			long_description=_('This UCC terminal server will be used for user logon UCC terminal servers.'),
			syntax=univention.admin.syntax.string,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'requiredObjectClasses': univention.admin.property(
			short_description=_('Required object classes'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'prohibitedObjectClasses': univention.admin.property(
			short_description=_('Excluded object classes'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'fixedAttributes': univention.admin.property(
			short_description=_('Fixed attributes'),
			long_description='',
			syntax=uccUserFixedAttributes,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'emptyAttributes': univention.admin.property(
			short_description=_('Empty attributes'),
			long_description='',
			syntax=uccUserFixedAttributes,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'filler': univention.admin.property(
			short_description='',
			long_description='',
			syntax=univention.admin.syntax.none,
			multivalue=0,
			required=0,
			may_change=1,
			identifies=0,
			dontsearch=1
		)
}
layout = [
	Tab(_('General'),_('UCC user session'), layout = [
		Group( _( 'General' ), layout = [
			'name',
			'session',
			'windowsDomain',
			'windowsTerminalserver',
			'uccTerminalserver',
		] ),
	] ),
	Tab(_('Object'),_('Object'), advanced = True, layout = [
		[ 'requiredObjectClasses' , 'prohibitedObjectClasses' ],
		[ 'fixedAttributes', 'emptyAttributes' ]
	] ),
]

mapping=univention.admin.mapping.mapping()
mapping.register('name', 'cn', None, univention.admin.mapping.ListToString)
mapping.register('session', 'univentionCorporateClientUserSession', None, univention.admin.mapping.ListToString)
mapping.register('windowsDomain', 'univentionCorporateClientUserWindowsDomain', None, univention.admin.mapping.ListToString)
mapping.register('windowsTerminalserver', 'univentionCorporateClientUserWindowsTerminalserver', None, univention.admin.mapping.ListToString)
mapping.register('uccTerminalserver', 'univentionCorporateClientUserUccTerminalserver', None, univention.admin.mapping.ListToString)

class object(univention.admin.handlers.simplePolicy):
	module=module

	def __init__(self, co, lo, position, dn='', superordinate=None, attributes=[]):
		global mapping
		global property_descriptions

		self.mapping=mapping
		self.descriptions=property_descriptions

		univention.admin.handlers.simplePolicy.__init__(self, co, lo, position, dn, superordinate)

	def exists(self):
		return self._exists
	
	def _ldap_pre_create(self):
		self.dn='%s=%s,%s' % (mapping.mapName('name'), mapping.mapValue('name', self.info['name']), self.position.getDn())

	def _ldap_addlist(self):
		return [ ('objectClass', ['top', 'univentionPolicy', 'univentionPolicyCorporateClientUser']) ]
	
def lookup(co, lo, filter_s, base='', superordinate=None, scope='sub', unique=0, required=0, timeout=-1, sizelimit=0):

	filter=univention.admin.filter.conjunction('&', [
		univention.admin.filter.expression('objectClass', 'univentionPolicyCorporateClientUser')
		])

	if filter_s:
		filter_p=univention.admin.filter.parse(filter_s)
		univention.admin.filter.walk(filter_p, univention.admin.mapping.mapRewrite, arg=mapping)
		filter.expressions.append(filter_p)

	res=[]
	try:
		for dn in lo.searchDn(unicode(filter), base, scope, unique, required, timeout, sizelimit):
			res.append(object(co, lo, None, dn))
	except:
		pass
	return res

def identify(dn, attr, canonical=0):
	return 'univentionCorporateClientUserSession' in attr.get('objectClass', [])
