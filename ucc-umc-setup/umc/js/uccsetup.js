/*
 * Copyright 2014 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/on",
	"dojo/topic",
	"dojox/html/styles",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Module",
	"umc/widgets/TextBox",
	"umc/widgets/CheckBox",
	"umc/widgets/ComboBox",
	"umc/widgets/Uploader",
	"umc/widgets/Text",
	"umc/widgets/Wizard",
	"./uccsetup/RadioButton",
	"umc/i18n!umc/modules/uccsetup"
], function(declare, lang, array, on, topic, styles, dialog, tools, Page, Form, ExpandingTitlePane, Module, TextBox, CheckBox, ComboBox, Uploader, Text, Wizard, RadioButton, _) {
	styles.insertCssRule('.umc-uccsetup-wizard-indent', 'margin-left: 26px;');
//	var modulePath = require.toUrl('umc/modules/uccsetup');
//	styles.insertCssRule('.umc-uccsetup-page > form > div', 'background-repeat: no-repeat; background-position: 10px 0px; padding-left: 200px; min-height: 200px;');
//	styles.insertCssRule('.umc-uccsetup-page .umcLabelPaneCheckBox', 'display: block !important;');
//	array.forEach(['start', 'credentials', 'config', 'info', 'syncconfig', 'syncconfig-left', 'syncconfig-right', 'syncconfig-left-right', 'msi', 'finished'], function(ipage) {
//		var conf = {
//			name: ipage,
//			path: modulePath
//		};
//		styles.insertCssRule(
//			lang.replace('.umc-uccsetup-page-{name} > form > div', conf),
//			lang.replace('background-image: url({path}/{name}.png)', conf)
//		);
//	});

	var _Wizard = declare("umc.modules.uccsetup.Wizard", [ Wizard ], {
		autoValidate: true,
		autoFocus: true,

		constructor: function() {
			this.pages = [{
				name: 'start',
				headerText: _('Univention Corporate Client configuration wizard'),
				helpText: _('<p>Welcome to the setup wizard of Univention Corporate Client (UCC).</p><p>UCC provides support for fully-featured Linux desktop systems running KDE (both stationary and notebooks) as well as support for Linux-based thin clients and access to terminal servers (Windows, Citrix XenApp, XRDP).</p>'),
				widgets: [{
					type: CheckBox,
					radioButtonGroup: 'config',
					name: 'fatclient',
					label: _('Configure support for Linux desktop systems'),
					labelConf: { style: 'margin-top: 0'	}
				}, {
					type: Text,
					name: 'helpFatclient',
					content: ('Linux desktops are installed via PXE netboot within only a few minutes. For this, 20 GBs of hard disk space and 1 GB RAM are required on the client computers.'),
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}, {
					type: CheckBox,
					radioButtonGroup: 'config',
					name: 'thinclient',
					label: _('Configure support for terminal services')
				}, {
					type: Text,
					name: 'helpThinclient',
					content: ('<p>Thin clients require 2 GB of local Compact Flash storage.</p><p>In case thin clients terminal server access shall be configured with a native RDP or Citrix on the thin clients, please refer to the manual TODO-DOC-LINK.</p>'),
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}]
			}, {
				name: 'download-fatclient',
				headerText: _('Download preconfigured UCC image'),
				helpText: _('<p>Univention provides a preconfigured desktop image based on KDE. It is regularly updated and offers a fully-featured KDE desktop environment.<p></p>Note that it is also possible to create custom images. This is documented in DOCREF.</p>'),
				widgets: [{
					type: CheckBox,
					name: 'download',
					label: _('Download UCC desktop image'),
					value: true
				}]
			}, {
				name: 'download-thinclient',
				headerText: _('Download preconfigured UCC image'),
				helpText: _('<p>Univention provides a preconfigured UCC thin client image which is regularly updated.</p><p>The thin client image allows access to various terminal services (Windows, Citrix XenApp, XRDP) and provides also a minimal local desktop. In addition to this, it is possible to configure a direct browser login to a preconfigured website, e.g, to access cloud-based web services.</p><p>Note that it is also possible to create custom images. This is documented in DOCREF.</p>'),
				widgets: [{
					type: CheckBox,
					name: 'download',
					label: _('Download UCC thin client image'),
					value: true
				}]
			}, {
				name: 'network',
				headerText: _('Network configuration'),
				helpText: _('Please specify the segment for client IP addresses.'),
				layout: [
					'useExistingNetwork', 'existingNetwork', 'createNewNetwork',
					['newNetworkAddress', 'newNetmask'],
					['newFirstIP', 'newLastIP']
				],
				widgets: [{
					type: RadioButton,
					radioButtonGroup: 'useNetwork',
					name: 'useExistingNetwork',
					label: _('Use an existing configuration'),
					checked: true,
					labelConf: { style: 'margin-top: 0'	}
				}, {
					type: ComboBox,
					name: 'existingNetwork',
					staticValues: [{id: 'default', label: '10.200.26.2 - 10.200.26.254'}],
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}, {
					type: RadioButton,
					radioButtonGroup: 'useNetwork',
					name: 'createNewNetwork',
					label: _('Specify a new IP segment')
				}, {
					type: TextBox,
					name: 'newNetworkAddress',
					label: _('Network'),
					disabled: true,
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}, {
					type: TextBox,
					name: 'newNetmask',
					label: _('Netmask'),
					disabled: true
				}, {
					type: TextBox,
					name: 'newFirstIP',
					label: _('First IP address'),
					disabled: true,
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}, {
					type: TextBox,
					name: 'newLastIP',
					label: _('Last IP address'),
					disabled: true
				}]
			}, {
				name: 'gateway',
				headerText: _('Configuration of default gateway'),
				helpText: _('No default gateway is assigned to the subnet. Which gateway should be configured for this network?'),
				widgets: [{
					type: TextBox,
					name: 'gateway',
					label: _('Default gateway'),
					value: '192.168.0.1'
				}]
			}, {
				name: 'terminalServices-thinclient',
				headerText: _('Configuration of terminal services'),
				helpText: _('Which terminal service shall be configured?'),
				widgets: [{
					type: CheckBox,
					name: 'rdp',
					label: _('Configure access to a Windows/XRDP terminal server')
				}, {
					type: CheckBox,
					name: 'citrix',
					label: _('Configure access to a Citrix XenApp server')
				}, {
					type: CheckBox,
					name: 'browser',
					label: _('Configure direct web browser access to a preconfigured web site')
				}]
			}, {
				name: 'terminalServices-thinclient-rdp',
				headerText: _('Configure acccess to Windows terminal/XRDP server'),
				helpText: _('This step allows the configuration of remote terminal server access using the RDP protocol. You can either access a Microsoft Windows terminal server (using a Windows-based desktop) or a XRDP terminal server (using a Linux-based KDE desktop). The setup of a XRDP terminal server is documented in TODODOC.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'host',
					label: _('Host name of terminal server')
				}, {
					type: TextBox,
					required: true,
					name: 'domain',
					label: _('Domain name (use xrdp1 for XRDP)')
				}, {
					type: CheckBox,
					name: 'sound',
					label: _('Enable sound'),
					value: true
				}, {
					type: CheckBox,
					name: 'usb',
					label: _('Enable USB storage passthrough'),
					value: true
				}, {
					type: CheckBox,
					name: 'rdpDefaultLogin',
					label: _('Make the RDP login the default session')
				}]
			}, {
				name: 'terminalServices-thinclient-citrix-upload',
				headerText: _('Configure access to Citrix XenApp server'),
				helpText: _('This step allows the configuration of a XenApp terminal server using the Citrix protocol. For this, Citrix Receiver will be integrated into the UCC thin client image.'),
				widgets: [{
					type: ComboBox,
					name: 'image',
					label: _('Please select the image into which Citrix Receiver should be integrated *** Only visible for entries >= 2 ***'),
					staticValues: ['UCC thin client image', 'Custom Ubuntun image']
				}, {
					type: Text,
					name: 'help',
					content: _('<p>For the configuration, it is necessary to manually download the i386 DEB version of the <a href="http://www.citrix.de/downloads/citrix-receiver/linux/receiver-for-linux-130.html">Citrix Receiver</a>.</p>')
				}, {
					type: Uploader,
					name: 'upload',
					label: _('<p>After the download has completed, please upload the Citrix Receiver DEB file to proceed.</p>')
				}, {
					type: CheckBox,
					name: 'eula',
					label: _('Confirm the End User License Agreement of Citrix Receiver [link].'),
					labelConf: { style: 'margin-top: 1.25em;' }
				}]
			}, {
				name: 'terminalServices-thinclient-citrix-login',
				headerText: _('Configure access to Citrix XenApp server'),
				helpText: _('Please specify the URL of the Citrix farm web interface for the user login.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'url',
					label: _('URL for Citrix farm login')
				}, {
					type: CheckBox,
					name: 'eula',
					label: _('Automatic Linux Desktop login')
				}]
			}, {
				name: 'terminalServices-thinclient-browser',
				headerText: _('Configure direct web browser access'),
				helpText: _('The Firefox session automatically starts a Firefox web browser session in fullscreen. This can be used to configure a direct browser login to a preconfigured website, e.g., to access cloud-based web services.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'host',
					label: _('Automatically connect to this web site')
				}]
			}, {
				name: 'defaultSession-thinclient',
				headerText: _('Default session'),
				helpText: _('Please configure the default session type.'),
				widgets: [{
					type: RadioButton,
					radioButtonGroup: 'session',
					name: 'rdp',
					label: _('Windows/XRDP terminal server'),
					labelConf: { style: 'margin-top: 0'	}
				}, {
					type: RadioButton,
					radioButtonGroup: 'session',
					name: 'citrix',
					label: _('Citrix XenApp server'),
					labelConf: { style: 'margin-top: 0'	}
				}, {
					type: RadioButton,
					radioButtonGroup: 'session',
					name: 'browser',
					label: _('Direct browser access'),
					labelConf: { style: 'margin-top: 0'	}
				}]
			}, {
				name: 'done',
				headerText: _('Configuration finished'),
				helpText: _('<p>Now you can create one or several clients. The images are rolled out using PXE.</p>')
					+ _('<p>The BIOS of the clients needs to have PXE/netboot enabled in its startup configuration. Once the client is started the installation is initiated and the client in joined into the UCS domain.</p>')
					+ _('<p>After a reboot you can log in and access configured services.</p>')
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);
			var syncmodeWidget = this.getWidget('start', 'syncmode');
		},

		_watchNetworkRadioButtons: function() {
			var existingNetworkComboBox = this.getWidget('network', 'existingNetwork');
			this.getWidget('network', 'useExistingNetwork').watch('checked', lang.hitch(this, function(attr, oldval, newval) {
				existingNetworkComboBox.set('disabled', !newval);
			}));

			var newNetworkWidgets = array.map(['newNetworkAddress', 'newNetmask', 'newFirstIP', 'newLastIP'], function(iname) {
				return this.getWidget('network', iname);
			}, this);
			this.getWidget('network', 'createNewNetwork').watch('checked', lang.hitch(this, function(attr, oldval, newval) {
				array.forEach(newNetworkWidgets, function(iwidget) {
					iwidget.set('disabled', !newval);
				});
			}));
		},

		_setLabelConf: function() {
			array.forEach(this.pages, function(ipageConf) {
				array.forEach(ipageConf.widgets, function(iwidgetConf) {
					var iwidget = this.getWidget(ipageConf.name, iwidgetConf.name);
					if (iwidget.labelConf && iwidget.$refLabel$) {
						tools.forIn(iwidget.labelConf, function(ikey, ival) {
							iwidget.$refLabel$.set(ikey, ival);
						}, this);
					}
				}, this);
			}, this);
		},

		postCreate: function() {
			this.inherited(arguments);
			this._watchNetworkRadioButtons();
			this._setLabelConf();
		},

		_getClientType: function() {
			var clientTypes = [];
			if (this.getWidget('start', 'fatclient').get('value')) {
				clientTypes.push('fatclient');
			}
			if (this.getWidget('start', 'thinclient').get('value')) {
				clientTypes.push('thinclient');
			}
			return clientTypes;
		},

		_terminalServices: ['rdp', 'citrix', 'browser'],
		_getTerminalServices: function() {
			return array.filter(this._terminalServices, function(itype) {
				return this.getWidget('terminalServices-thinclient', itype).get('value');
			}, this);
		},

		_isPageForClientType: function(pageName) {
			if (pageName.indexOf('-') < 0) {
				return true;
			}
			var match = array.filter(this._getClientType(), function(clientType) {
				var suffix = '-' + clientType;
				return pageName.indexOf(suffix) >= 0;
			});
			return match.length > 0;
		},

		_isPageForTerminalServiceType: function(pageName) {
			// page is visible if it does not contain a suffix indicating a specific terminal service
			var i, suffix;
			var isPageTerminalServiceSpecific = false;
			for (i = 0; i < this._terminalServices.length; ++i) {
				suffix = '-' + this._terminalServices[i];
				if (pageName.indexOf(suffix) >= 0) {
					isPageTerminalServiceSpecific = true;
					break;
				}
			}
			if (!isPageTerminalServiceSpecific) {
				return true;
			}

			// check for specific terminal service suffix
			var terminalServices = this._getTerminalServices();
			for (i = 0; i < terminalServices.length; ++i) {
				suffix = '-' + terminalServices[i];
				if (pageName.indexOf(suffix) >= 0) {
					return true;
				}
			}
			return false;
		},

		next: function(pageName) {
			var _inheritedNext = lang.hitch(this, this.inherited, arguments);
			var nextPage = _inheritedNext();
			while (!(this._isPageForClientType(nextPage) && this._isPageForTerminalServiceType(nextPage))) {
				nextPage = _inheritedNext([nextPage]);
			}
			return nextPage;
		},

		previous: function(pageName) {
			var _inheritedNext = lang.hitch(this, this.inherited, arguments);
			var previousPage = _inheritedNext();
			while (!(this._isPageForClientType(previousPage) && this._isPageForTerminalServiceType(previousPage))) {
				previousPage = _inheritedNext([previousPage]);
			}
			return previousPage;
		},

		hasNext: function(pageName) {
			return this.inherited(arguments);
		},

		hasPrevious: function(pageName) {
			return this.inherited(arguments);
		},

		canCancel: function(pageName) {
			return this.inherited(arguments);
		}
	});

	return declare("umc.modules.uccsetup", Module, {
		unique: true,

		buildRendering: function() {
			//var progressBar = new ProgressBar({});
			this.inherited(arguments);

			this.wizard = new _Wizard({
				//progressBar: progressBar
			});
			this.addChild(this.wizard);
			this.wizard.on('Finished', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
			this.wizard.on('Cancel', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
		}

	});
});
