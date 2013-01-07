# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  UDM policy for the ucc desktop settings
#
# Copyright 2013 Univention GmbH
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

from univention.admin.layout import Tab, Group
import univention.admin.syntax
import univention.admin.filter
import univention.admin.handlers
import univention.admin.localization

import univention.debug

translation=univention.admin.localization.translation('univention.admin.handlers.ucc-policies')
_=translation.translate

class uccDesktopFixedAttributes(univention.admin.syntax.select):
	name='uccDesktopFixedAttributes'
	choices=[
		( 'environmentVars', _('UCC desktop environment variables') )
		]

module='policies/ucc_desktop'
operations=['add','edit','remove','search']

policy_oc='univentionPolicyCorporateClientDesktop'
policy_apply_to=["users/user"]
policy_position_dn_prefix="cn=ucc"

childs=0
short_description=_('Policy: Univention Corporate Client desktop settings')
policy_short_description=_('UCC desktop settings')
long_description=''
options={
}
property_descriptions={
	'name': univention.admin.property(
			short_description=_('Name'),
			long_description='',
			syntax=univention.admin.syntax.policyName,
			multivalue=0,
			include_in_default_search=1,
			options=[],
			required=1,
			may_change=0,
			identifies=1,
		),
	'environmentVars': univention.admin.property(
			short_description=_('UCC desktop environment variables'),
			long_description='',
			syntax=univention.admin.syntax.UCR_Variable,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0,
		),
	'logonScripts': univention.admin.property(
			short_description=_('Desktop Logon scripts'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'logoutScripts': univention.admin.property(
			short_description=_('Desktop Logout scripts'),
			long_description='',
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
			syntax=uccDesktopFixedAttributes,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'emptyAttributes': univention.admin.property(
			short_description=_('Empty attributes'),
			long_description='',
			syntax=uccDesktopFixedAttributes,
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
	Tab(_('General'),_('Desktop settings'), layout = [
		Group( _( 'General' ), layout = [
			'name',
			'environmentVars',
			['logonScripts', 'logoutScripts'],
		] ),
	] ),
	Tab(_('Object'),_('Object'), advanced = True, layout = [
		[ 'requiredObjectClasses' , 'prohibitedObjectClasses' ],
		[ 'fixedAttributes', "emptyAttributes" ]
	] ),
]

mapping=univention.admin.mapping.mapping()
mapping.register('name', 'cn', None, univention.admin.mapping.ListToString)
mapping.register('logonScripts', 'univentionCorporateClientDesktopLogon')
mapping.register('logoutScripts', 'univentionCorporateClientDesktopLogout')

class object(univention.admin.handlers.simplePolicy):
	module=module

	def __init__(self, co, lo, position, dn='', superordinate=None, attributes = [] ):
		global mapping
		global property_descriptions

		self.mapping=mapping
		self.descriptions=property_descriptions

		univention.admin.handlers.simplePolicy.__init__(self, co, lo, position, dn, superordinate, attributes )
		
		self.save()

	def _post_unmap( self, info, values ):
		info[ 'environmentVars' ] = []
		for key, value in values.items():
			if key.startswith( 'univentionCorporateClientDesktopEnv;entry-hex-' ):
				key_name = key.split( 'univentionCorporateClientDesktopEnv;entry-hex-', 1 )[ 1 ].decode( 'hex' )
				info[ 'environmentVars' ].append( ( key_name, values[ key ][ 0 ].strip() ) )
		return info

	def _post_map( self, modlist, diff ):
		for key, old, new in diff:
			if key == 'environmentVars':
				old_dict = dict( old )
				new_dict = dict( new )
				for var, value in old_dict.items():
					attr_name = 'univentionCorporateClientDesktopEnv;entry-hex-%s' % var.encode( 'hex' )
					if not var in new_dict: # variable has been removed
						modlist.append( ( attr_name, value, None ) )
					elif value != new_dict[ var ]: # value has been changed
						modlist.append( ( attr_name, value, new_dict[ var ] ) )
				for var, value in new_dict.items():
					attr_name = 'univentionCorporateClientDesktopEnv;entry-hex-%s' % var.encode( 'hex' )
					if var not in old_dict: # variable has been added
						modlist.append( ( attr_name, None, new_dict[ var ] ) )
				break

		return modlist

	def _custom_policy_result_map( self ):
		values = {}
		self.polinfo_more[ 'environmentVars' ] = []
		for attr_name, value_dict in self.policy_attrs.items():
			values[ attr_name ] = value_dict[ 'value' ]
			if attr_name.startswith( 'univentionCorporateClientDesktopEnv;entry-hex-' ):
				key_name = attr_name.split( 'univentionCorporateClientDesktopEnv;entry-hex-', 1 )[ 1 ].decode( 'hex' )
				value_dict[ 'value' ].insert( 0, key_name )
				self.polinfo_more[ 'environmentVars' ].append( value_dict )
			elif attr_name:
				self.polinfo_more[ self.mapping.unmapName( attr_name ) ] = value_dict

		self.polinfo = univention.admin.mapping.mapDict( self.mapping, values )
		self.polinfo = self._post_unmap( self.polinfo, values )

	def exists(self):
		return self._exists

	def _ldap_pre_create(self):
		self.dn='%s=%s,%s' % (mapping.mapName('name'), mapping.mapValue('name', self.info['name']), self.position.getDn())

	def _ldap_addlist(self):
		return [ ('objectClass', ['top', 'univentionPolicy', 'univentionPolicyCorporateClientDesktop']) ]
	
def lookup(co, lo, filter_s, base='', superordinate=None, scope='sub', unique=0, required=0, timeout=-1, sizelimit=0):

	filter=univention.admin.filter.conjunction('&', [
		univention.admin.filter.expression('objectClass', 'univentionPolicyCorporateClientDesktop')
		])

	if filter_s:
		filter_p=univention.admin.filter.parse(filter_s)
		univention.admin.filter.walk(filter_p, univention.admin.mapping.mapRewrite, arg=mapping)
		filter.expressions.append(filter_p)

	res=[]
	try:
		for dn, attrs in lo.search(unicode(filter), base, scope, [], unique, required, timeout, sizelimit):
			res.append( object( co, lo, None, dn, attributes = attrs ) )
	except:
		pass
	return res

def identify(dn, attr, canonical=0):
	return 'univentionPolicyCorporateClientDesktop' in attr.get('objectClass', [])


