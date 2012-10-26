# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  UDM policy for thin client session 
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

import re, sys, string
from univention.admin.layout import Tab, Group
import univention.admin.filter
import univention.admin.handlers
import univention.admin.syntax
import univention.admin.localization
import univention.admin.uexceptions

translation=univention.admin.localization.translation('univention.admin.handlers.ucc-policies')
_=translation.translate

module = 'settings/ucc_image'

childs = 0
short_description = _('UCC images')
long_description = ''
operations = [ 'search', 'edit', 'add', 'remove' ]
superordinate='settings/cn'

property_descriptions={
	'name': univention.admin.property(
			short_description= _('Image name'),
			long_description= _('Name of the image'),
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=1,
			may_change=1,
			identifies=1
		),
	'description': univention.admin.property(
			short_description= _('Description'),
			long_description= _('Description of image'),
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'server': univention.admin.property(
			short_description= _('Server'),
			long_description= _('The image is available on these servers'),
			syntax=univention.admin.syntax.UCS_Server,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
}


layout = [
	Tab(_('General'),_('UCC session script'), layout = [
		Group( _( 'General' ), layout = [
			'name',
			'description',
			'server'
                        ] ),
                ] )
]


mapping=univention.admin.mapping.mapping()
mapping.register('name', 'univentionCorporateClientImageName', None, univention.admin.mapping.ListToString)
mapping.register('description', 'description', None, univention.admin.mapping.ListToString)
mapping.register('server', 'univentionCorporateClientImageServer')


class object(univention.admin.handlers.simpleLdap):
	module=module

	def __init__(self, co, lo, position, dn='', superordinate=None, attributes=[]):
		global mapping
		global property_descriptions

		self.co=co
		self.lo=lo
		self.dn=dn
		self.position=position
		self._exists=0
		self.mapping=mapping
		self.descriptions=property_descriptions

		univention.admin.handlers.simpleLdap.__init__(self, co, lo, position, dn, superordinate)

	def exists(self):
		return self._exists

	def _ldap_pre_create(self):
		self.dn='%s=%s,%s' % (mapping.mapName('name'), mapping.mapValue('name', self.info['name']), self.position.getDn())

	def _ldap_addlist(self):
		return [ ('objectClass', [ 'univentionCorporateClientImage' ] ) ]

def lookup(co, lo, filter_s, base='', superordinate=None, scope='sub', unique=0, required=0, timeout=-1, sizelimit=0):
	filter=univention.admin.filter.conjunction('&', [
				univention.admin.filter.expression('objectClass', 'univentionCorporateClientImage'),
				])

	if filter_s:
		filter_p=univention.admin.filter.parse(filter_s)
		univention.admin.filter.walk(filter_p, univention.admin.mapping.mapRewrite, arg=mapping)
		filter.expressions.append(filter_p)

	res=[]
	for dn in lo.searchDn(unicode(filter), base, scope, unique, required, timeout, sizelimit):
		res.append(object(co, lo, None, dn))
	return res


def identify(dn, attr, canonical=0):
	return 'univentionCorporateClientImage' in attr.get('objectClass', [])

