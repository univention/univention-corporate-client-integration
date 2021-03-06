# -*- coding: utf-8 -*-
#
# UCC PXE Boot
#  Univention Listener Module
#
# Copyright (C) 2001-2016 Univention GmbH
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

__package__ = ''  # workaround for PEP 366

name = 'uccpxeboot'
description = 'PXE configuration for UCC clients'
filter = '(objectClass=univentionCorporateClient)'
attributes = []

import listener
import os
import ldap
import string
import univention.debug
import univention.config_registry

pxebase = '/var/lib/univention-client-boot/pxelinux.cfg'


def ip_to_hex(ip):
	if ip.count('.') != 3:
		return ''
	o = ip.split('.')
	return '%02X%02X%02X%02X' % (int(o[0]), int(o[1]), int(o[2]), int(o[3]))


def handler(dn, new, old):

	configRegistry = univention.config_registry.ConfigRegistry()
	configRegistry.load()

	# remove pxe host file
	if old and old.get('aRecord'):
		basename = ip_to_hex(old['aRecord'][0])
		if not basename:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'PXE: invalid IP address %s' % old['aRecord'][0])
			return
		filename = os.path.join(pxebase, basename)
		if os.path.exists(filename):
			listener.setuid(0)
			try:
				os.unlink(filename)
			finally:
				listener.unsetuid()

	# create pxe host file(s)
	if new and new.get('cn') and new.get('aRecord'):

		cn = new['cn'][0]
		univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'PXE: writing configuration for host %s' % cn)

		if 'univentionCorporateClientBootVariant' in new \
				and new.get('univentionCorporateClientBootVariant')[0] == "localboot":
			pxeconfig = \
'''
DEFAULT local
LABEL local
LOCALBOOT 0
'''
		else:
			image = new.get('univentionCorporateClientBootImage', [None])[0]
			if not image:
				image = configRegistry.get('ucc/pxe/image')
				if not image:
					univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'PXE: no boot image specified for %s' % cn)
					return
			initrd = '%s.initrd' % image
			kernel = '%s.kernel' % image

			server = configRegistry['ucc/pxe/nfsroot']
			if new.get('univentionCorporateClientDedicatedImageServer'):
				server = new['univentionCorporateClientDedicatedImageServer'][0]
			append = 'root=/dev/nfs '
			append += 'nfsroot=%s:/var/lib/univention-client-boot ' % server

			if configRegistry.get('ucc/pxe/vga'):
				append += 'vga=%s ' % configRegistry['ucc/pxe/vga']
			append += 'initrd=%s ' % initrd
			if configRegistry.is_true('ucc/pxe/quiet', False):
				append += 'quiet '
			if configRegistry.is_true('ucc/pxe/traditionalinterfacenames', True):
				append += 'net.ifnames=0 biosdevname=0 '
			if 'xorg/keyboard/options/XkbLayout' in configRegistry.keys():
				append += 'keyboard=%s ' % configRegistry['xorg/keyboard/options/XkbLayout']
			if 'locale/default' in configRegistry.keys():
				append += 'locale=%s ' % configRegistry['locale/default']
			if 'ucc/pxe/timezone' in configRegistry.keys():
				append += 'timezone=%s ' % configRegistry['ucc/pxe/timezone']
			if 'ucc/pxe/append' in configRegistry.keys():
				append += '%s ' % configRegistry['ucc/pxe/append']
			if configRegistry.get('ucc/pxe/loglevel', False):
				append += 'loglevel=%s ' % configRegistry['ucc/pxe/loglevel']
			if configRegistry.is_true("ucc/pxe/bootsplash", False):
				append += 'splash '
			append += 'boot=ucc '
			if new.get('univentionCorporateClientBootVariant'):
				append += 'ucc=%s ' % new.get('univentionCorporateClientBootVariant')[0]
			if image != 'none':
				append += 'image=%s ' % image
			if new.get('univentionCorporateClientBootRepartitioning', ['FALSE'])[0] == 'TRUE':
				append += 'repartition=y '
			if new.get('univentionCorporateClientBootParameter'):
				append += string.join(new.get('univentionCorporateClientBootParameter', ' '))

			append += '\n'

			ipappend = configRegistry.get('pxe/ucc/ipappend', "3")

			pxeconfig = \
'''
PROMPT 0
DEFAULT UCC
IPAPPEND %s

APPEND %s

LABEL UCC
	KERNEL %s
''' % (ipappend, append, kernel)

		basename = ip_to_hex(new['aRecord'][0])
		if not basename:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'PXE: invalid IP address %s' % new['aRecord'][0])
			return
		filename = os.path.join(pxebase, basename)

		listener.setuid(0)
		try:
			f = open(filename, 'w')
			f.write('# This file is auto generated by the UCS listener module uccpxeboot\n')
			f.write('# PXE configuration for %s (%s)\n' % (new.get('cn', [])[0], new.get('aRecord', [])[0]))
			f.write(pxeconfig)
			f.close()
		finally:
			listener.unsetuid()
