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
	"dojo/topic",
	"dojo/promise/all",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/ProgressBar",
	"umc/widgets/Module",
	"umc/widgets/TextBox",
	"umc/widgets/CheckBox",
	"umc/widgets/ComboBox",
	"umc/widgets/Uploader",
	"umc/widgets/Text",
	"umc/widgets/Wizard",
	"umc/widgets/RadioButton",
	"umc/i18n!umc/modules/uccsetup",
	"xstyle/css!./uccsetup.css"
], function(declare, lang, array, topic, all, dialog, tools, ProgressBar, Module, TextBox, CheckBox, ComboBox, Uploader, Text, Wizard, RadioButton, _) {
	var _regIPv4 =  /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$/;
	var _regURL =  /^https?:\/\//;
	var _regDebianI386 = /_i386.deb$/;

	var _Wizard = declare("umc.modules.uccsetup.Wizard", [ Wizard ], {
		autoValidate: true,
		autoFocus: true,
		autoHeight: true,
		'class': 'umc-uccsetup-wizard',
		__info: {},
		_infoDeferred: null,
		_progressBar: null,

		// taken from: http://stackoverflow.com/a/9221063
		constructor: function() {
			this.pages = [{
				name: 'start',
				headerText: _('Univention Corporate Client configuration wizard'),
				helpText: _('<p>Welcome to the setup wizard for Univention Corporate Client (UCC)!</p><p>UCC allows the operation and management of Linux desktop systems as well as thin clients for accessing remote desktop services (terminal servers) via RDP and Citrix XenApp (ICA). Further information can be found in the <a href="http://docs.univention.de/en/ucc2.0.html" target="_blank">UCC manual</a>.</p>'),
				widgets: [{
					type: CheckBox,
					name: 'fatclient',
					label: _('<b>Linux desktop systems configuration / XRDP terminal server setup</b>'),
					labelConf: { 'class': 'umc-uccsetup-wizard-no-margin-bottom' }
				}, {
					type: Text,
					name: 'helpFatclient',
					content: _('<p>This option allows the installation of desktops via PXE netboot. With UCC, Linux desktops can also be accessed as remote desktops via the RDP protocol. Please check this option for remote desktop configuration.</p>'),
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}, {
					type: CheckBox,
					name: 'thinclient',
					label: _('<b>Thin client configuration</b>'),
					labelConf: { 'class': 'umc-uccsetup-wizard-no-margin-bottom' }
				}, {
					type: Text,
					name: 'helpThinClient',
					content: _('<p>UCC provides a thin client image which can be installed on thin clients with at least 2 GB of Compact Flash storage.</p><p>UCC thin clients can access RDP and Citrix terminal services or they can be configured for direct access to a specific web site (e.g., for cloud based services).</p>'),
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}]
			}, {
				name: 'download-fatclient',
				headerText: _('Download preconfigured UCC desktop image'),
				helpText: _('<p>Univention provides a preconfigured desktop image based on Kubuntu 14.04. The image is regularly updated and offers a fully-featured KDE desktop environment.</p><p>Note that it is also possible to create custom images. This is documented in the <a href="http://docs.univention.de/en/ucc2.0.html" target="_blank">UCC manual</a>.</p>'),
				widgets: [{
					type: CheckBox,
					name: 'download',
					label: _('Download UCC desktop image'),
					value: true
				}]
			}, {
				name: 'download-thinclient',
				headerText: _('Download preconfigured UCC thinclient image'),
				helpText: _('<p>Univention provides a preconfigured UCC thin client image which is regularly updated.</p><p>The thin client image allows access to various terminal services (Windows, Citrix, XRDP) and provides also a minimal local LXDE desktop. In addition to this, it is possible to configure a direct browser login to a preconfigured website, e.g, to access cloud-based web services.</p><p>Note that it is also possible to create custom images. This is documented in the <a href="http://docs.univention.de/en/ucc2.0.html" target="_blank">UCC manual</a>.</p>'),
				widgets: [{
					type: CheckBox,
					name: 'download',
					label: _('Download UCC thin client image'),
					value: true,
					onChange: lang.hitch(this, '_updateDownloadThinClient')
				}]
			}, {
				name: 'network',
				headerText: _('Network configuration'),
				helpText: _('<p>UCS uses so-called network objects for managing IP adresses and the DNS/DHCP configuration of the clients. Network objects specify IP address ranges and provide the next available IP address when creating a new computer entry.</p><p>You can either use an existing network object or create a new one. The <b>default</b> network is created during the installation of the UCS master domain controller. If you want to separate the IP addresses of the UCS servers and the UCC clients it is recommended to create a new network object.'),
				layout: [
					'useExistingNetwork', 'existingNetwork', 'createNewNetwork',
					['newNetworkAddress', 'newNetmask'],
					['newFirstIP', 'newLastIP']
				],
				widgets: [{
					type: RadioButton,
					radioButtonGroup: 'useNetwork',
					name: 'useExistingNetwork',
					label: _('Use an existing network object'),
					checked: true
				}, {
					type: ComboBox,
					name: 'existingNetwork',
					dynamicValues: 'uccsetup/info/networks',
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' }
				}, {
					type: RadioButton,
					radioButtonGroup: 'useNetwork',
					name: 'createNewNetwork',
					label: _('Create a new network object'),
					labelConf: { 'class': 'umc-uccsetup-wizard-margin-top' }
				}, {
					type: TextBox,
					name: 'newNetworkAddress',
					label: _('Network address (e.g., 192.168.10.0)'),
					required: true,
					disabled: true,
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' },
					validator: function(value) {
						return _regIPv4.test(value);
					},
					onChange: lang.hitch(this, '_updateNetworkDefaults')
				}, {
					type: TextBox,
					name: 'newNetmask',
					label: _('Netmask'),
					required: true,
					disabled: true
				}, {
					type: TextBox,
					name: 'newFirstIP',
					label: _('First IP address'),
					disabled: true,
					labelConf: { 'class': 'umc-uccsetup-wizard-indent' },
					validator: function(value) {
						return _regIPv4.test(value);
					}
				}, {
					type: TextBox,
					name: 'newLastIP',
					label: _('Last IP address'),
					disabled: true,
					validator: function(value) {
						return _regIPv4.test(value);
					}
				}]
			}, {
				name: 'gateway',
				headerText: _('Configuration of default gateway'),
				helpText: _('No default gateway is currently assigned to the subnet via DHCP. Which gateway should be configured for this network? (In most cases the default gateway of the UCS server can be used.)'),
				widgets: [{
					type: TextBox,
					name: 'gateway',
					label: _('Default gateway'),
					required: true
				}]
			}, {
				name: 'terminalServices-thinclient',
				headerText: _('Configuration of remote desktop services'),
				helpText: _('Which access to remote desktop services shall be configured?'),
				widgets: [{
					type: CheckBox,
					name: 'rdp',
					label: _('RDP services (Windows Remote Desktop Services, XRDP)')
				}, {
					type: CheckBox,
					name: 'citrix',
					label: _('Citrix')
				}, {
					type: CheckBox,
					name: 'browser',
					label: _('Preconfigured web site')
				}]
			}, {
				name: 'terminalServices-thinclient-rdp',
				headerText: _('Configure acccess to RDP services'),
				helpText: _('<p>This step allows to configure access to a remote terminal server using the RDP protocol.</p><p>You can either access a Microsoft Windows terminal server (using a Windows-based desktop) or an XRDP terminal server (using a Linux-based KDE desktop). To configure an XRDP terminal server, please use the <b>Linux desktop systems configuration / XRDP terminal server</b> option of the UCC setup wizard.</p>'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'host',
					label: _('Host name of RDP server')
				}, {
					type: TextBox,
					name: 'domain',
					label: _('Domain name (leave empty when connecting to an XRDP terminal server)')
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
				}]
			}, {
				name: 'terminalServices-thinclient-citrix-upload',
				headerText: _('Configure access to Citrix services'),
				helpText: _('This step allows to configure the access to Citrix services. For this, Citrix Receiver will be integrated into the UCC thin client image (it cannot be distributed in the standard UCC images due to license restrictions).'),
				widgets: [{
					type: ComboBox,
					name: 'image',
					label: _('Please select the image into which Citrix Receiver should be integrated.'),
					dynamicValues: 'uccsetup/info/ucc_images'
				}, {
					type: Text,
					name: 'fileExists',
					content: '',  // will be set via this._updateCitrixReceiverUploadPage()
					visible: false,
					labelConf: { 'class': 'umc-uccsetup-wizard-margin-top' }
				}, {
					type: Text,
					name: 'help',
					content: _('<p>For the configuration, it is necessary to manually download the 32-bit DEB version of the <a href="http://www.citrix.de/downloads/citrix-receiver/linux/receiver-for-linux-131.html" target="_blank">Citrix Receiver for Linux</a> and save it somewhere on your desktop.</p>')
				}, {
					type: Uploader,
					name: 'upload',
					label: _('<p>After the download has completed, please upload the Citrix Receiver DEB file to proceed. The Citrix Receiver is the automatically installed into the selected image.</p>'),
					command: 'uccsetup/upload',
					showClearButton: false,
					maxSize: 30000000,
					canUpload: lang.hitch(this, '_checkUploadFile'),
					onProgress: lang.hitch(this, function(info) {
						this._progressBar.setInfo(null, null, info.decimal * 100);
					}),
					onError: lang.hitch(this, function(err) {
						this.standby(false);
					}),
					onUploaded: lang.hitch(this, function(info) {
						this.standby(false);
						this._setCitrixReceiverUploaded(true);
					}),
					onUploadStarted: lang.hitch(this, function(info) {
						this.standby(false);
						this._progressBar.reset(_('Uploading file'));
						this.standby(true, this._progressBar);
					})
				}, {
					type: CheckBox,
					name: 'eula',
					label: _('Confirm the End User License Agreement of Citrix Receiver (as presented during the download of the Citrix Receiver).'),
					labelConf: { 'class': 'umc-uccsetup-wizard-margin-top' }
				}]
			}, {
				name: 'terminalServices-thinclient-citrix-login',
				headerText: _('Configure access to Citrix services'),
				helpText: _('Please specify the URL of the Citrix web login.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'url',
					label: _('URL for Citrix login (e.g., <span style="text-decoration: underline">http://citrix.example.com/StoreServiceWeb</span> )'),
					validator: function(value) {
						return _regURL.test(value);
					}
				}, {
					type: CheckBox,
					name: 'autoLogin',
					label: _('Automatic thin client login (the actual authentication occurs on the Citrix web interface)'),
					value: true
				}]
			}, {
				name: 'terminalServices-thinclient-browser',
				headerText: _('Configure web site access'),
				helpText: _('This step allows to configure of direct access to a web site, e.g., to access cloud-based web services. For this the web browser Firefox will be launched automatically in fullscreen mode.'),
				widgets: [{
					type: TextBox,
					required: true,
					name: 'url',
					label: _('Automatically connect to this web site (e.g., <span style="text-decoration: underline">http://intranet.example.com/groupware</span> )'),
					validator: function(value) {
						return _regURL.test(value);
					}
				}]
			}, {
				name: 'confirm',
				headerText: _('Confirm configuration settings'),
				helpText: _('Please confirm the chosen UCC configuration:'),
				widgets: [{
					type: Text,
					name: 'summary',
					content: ''
				}]
			}, {
				name: 'error',
				headerText: _('UCC wizard - An error ocurred'),
				helpText: _('An error occurred during the configuration of UCC. The following information will give you some more details on which problems occurred during the installation process.'),
				widgets: [{
					type: Text,
					name: 'info',
					style: 'font-style:italic;',
					content: ''
				}]
			}, {
				name: 'done',
				headerText: _('Configuration finished'),
				helpText: this._getHelpTextForDonePage()
			}];
		},

		_getHelpTextForDonePage: function() {
			var text = '';
			try {
				require('umc/modules/udm');
				text += _('<p>Now you can create one or several clients in the <a href="javascript:void(0)" onclick="require(\'umc/app\').openModule(\'udm\', \'computers/computer\')">computer management module</a> by clicking on <b>Add</b>.</p>');
			} catch(e) {
				text += _('<p>Now you can create one or several clients in the <i>computer management module</i> on the DC master system of your domain by clicking on <b>Add</b>.</p>');
			}
			text += '<ol>'
				+ '<li>'
				+ _('<p>Depending on whether the client is a desktop or thin client, the fitting <b>Container</b> should be selected.</p>')
				+ _('<p>To configure a UCC system as an XRDP terminal server you need to select the desktop image and create the client in <i>ucc-xrdpserver</i> container. A software installation policy is bound to this container. After a reboot the <b>univention-xrdp</b> package is installed automatically.</p>')
				+ '</li>'
				+ _('<li>Select <i>Univention Corporate Client</i> as the <b>Type</b> of computer. </li>')
				+ _('<li>Enter the <i>Hostname</i> of the client. </li>')
				+ _('<li>When selecting <b>Network</b> created earlier, a free IP address is proposed. The MAC address of the client needs to be specified for a working DHCP configuration. </li>')
				+ _('<li>Now click <i>Next</i>. </li>')
				+ _('<li><i>Installation with repartitioning and image rollout</i> should be selected as the <b>Boot variant</b> along with the designated image. Warning: All data on that system is lost! If you only want to try UCC without installing it on the hard drive, you can alternatively select <i>Live system</i>. </li>')
				+ '</ol>'
				+ _('<p>The images are rolled out using PXE after booting a system. Thus, the BIOS of the clients needs to have PXE/netboot enabled in its startup configuration. Once the client is started the installation is initiated and the client is joined into the UCS domain.</p>')
				+ _('<p>After successful installation you can log in with any domain user.</p>');
			return text;
		},

		buildRendering: function() {
			this.inherited(arguments);
			this._queryInfo();
			this._progressBar = new ProgressBar({});
			this.own(this._progressBar);
			this.standby(true);
			this._ready().then(lang.hitch(this, 'standby', false));

			// change labels of default footer buttons
			this.getPage('confirm')._footerButtons.next.set('label', _('Apply configuration'));
			this.getPage('error')._footerButtons.next.set('label', _('Retry'));
		},

		postCreate: function() {
			this.inherited(arguments);
			this._setDefaultValues();
			this._watchNetworkRadioButtons();
			this._setLabelConf();
			var networkAddressWidget = this.getWidget('network', 'newNetworkAddress');
			networkAddressWidget.on('keyup', lang.hitch(this, '_updateNetworkDefaults'));
			this._setCitrixReceiverUploaded(false);
		},

		_checkUploadFile: function(fileInfo) {
			if (!_regDebianI386.test(fileInfo.name)) {
				dialog.alert(_('The specified file needs to be a Debian package (file ending .deb) for the 32 bit system architecture.'));
				return false;
			}
			return true;
		},

		_setCitrixReceiverUploaded: function(uploaded) {
			this.getPage('terminalServices-thinclient-citrix-upload')._footerButtons.next.set('disabled', !uploaded);
			var eula = this.getWidget('terminalServices-thinclient-citrix-upload', 'eula');
			eula.set('disabled', !uploaded);
		},

		_queryInfo: function() {
			this._infoDeferred = tools.umcpCommand('uccsetup/info').then(lang.hitch(this, function(response) {
				this._info = response.result;
				return response.result;
			}));
		},

		_setDefaultValues: function() {
			this._infoDeferred.then(lang.hitch(this, function(info) {
				this.getWidget('gateway', 'gateway').set('value', info.gateway);

				if (info.rdp_host) {
					// only set if rdp is configured
					array.forEach(['host', 'domain', 'sound', 'usb'], function(ikey) {
						this.getWidget('terminalServices-thinclient-rdp', ikey).set('value', info['rdp_' + ikey]);
					}, this);
				}

				if (info.citrix_url) {
					// only set if citrix is configured
					this.getWidget('terminalServices-thinclient-citrix-login', 'autoLogin').set('value', info.citrix_autologin);
				}
				this.getWidget('terminalServices-thinclient-citrix-upload', 'eula').set('value', info.citrix_accepteula);
				this.getWidget('terminalServices-thinclient-citrix-login', 'url').set('value', info.citrix_url);

				this.getWidget('terminalServices-thinclient-browser', 'url').set('value', info.browser_url);
				this._updateCitrixReceiverUploadPage();
			}));
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

		// apply config properties (esp. CSS styling) to label widgets
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

		getValues: function() {
			var vals = {};
			vals.fatclient = this.getWidget('start', 'fatclient').get('value');
			vals.thinclient = this.getWidget('start', 'thinclient').get('value');

			// downloads
			vals.downloadThinClientImage = this.getWidget('download-thinclient', 'download').get('value') && vals.thinclient && !this._info.has_installed_ucc_thinclient;
			vals.downloadFatClientImage = this.getWidget('download-fatclient', 'download').get('value') && vals.fatclient && !this._info.has_installed_ucc_desktop;

			// network configuration
			vals.network = {};
			var useExistingNetwork = this.getWidget('network', 'useExistingNetwork').get('value');
			if (useExistingNetwork) {
				vals.network.existingDN = this.getWidget('network', 'existingNetwork').get('value');
			}
			else {
				tools.forIn({
					address: 'newNetworkAddress',
					mask: 'newNetmask',
					firstIP: 'newFirstIP',
					lastIP: 'newLastIP'
				}, function(key1, key2) {
					vals.network[key1] = this.getWidget('network', key2).get('value');
				}, this);
			}

			// gateway configuration
			if (this._isPageVisible('gateway')) {
				vals.gateway = this.getWidget('gateway', 'gateway').get('value');
			}

			// thinclient configuration
			if (vals.thinclient) {
				var terminalServices = {};
				array.forEach(this._getTerminalServices(), function(iservice) {
					terminalServices[iservice] = true;
				});

				// RDP service configuration
				if (terminalServices.rdp) {
					vals.rdp = {};
					array.forEach(['host', 'domain', 'sound', 'usb'], function(ikey) {
						vals.rdp[ikey] = this.getWidget('terminalServices-thinclient-rdp', ikey).get('value');
					}, this);
				}

				// Citrix configuration
				if (terminalServices.citrix) {
					vals.citrix = {
						image: this.getWidget('terminalServices-thinclient-citrix-upload', 'image').get('value'),
						url: this.getWidget('terminalServices-thinclient-citrix-login', 'url').get('value'),
						autoLogin: this.getWidget('terminalServices-thinclient-citrix-login', 'autoLogin').get('value')
					};
				}

				// browser configuration
				if (terminalServices.browser) {
					vals.browser = {
						url: this.getWidget('terminalServices-thinclient-browser', 'url').get('value')
					};
				}
			}

			return vals;
		},

		_updateDownloadThinClient: function() {
			var downloadThinClient = this.getWidget('download-thinclient', 'download').get('value');
			var staticValues = [];
			if (downloadThinClient && this._isPageVisible('download-thinclient')) {
				staticValues = [{
					id: '_DEFAULT_',
					label: _('Downloaded UCC thin client image')
				}];
			}
			var uccImageWidget = this.getWidget('terminalServices-thinclient-citrix-upload', 'image');
			uccImageWidget.set('staticValues', staticValues);
			uccImageWidget.setInitialValue(null);
		},

		_updateNetworkDefaults: function() {
			var networkAddress = this.getWidget('network', 'newNetworkAddress').get('value');
			if (!_regIPv4.test(networkAddress)) {
				// no valid IP address
				return;
			}
			var subnet = networkAddress.split('.').slice(0, 3).join('.');

			tools.forIn({
				newNetmask: '24',
				newFirstIP: '{0}.2',
				newLastIP: '{0}.254'
			}, function(ikey, ivalue) {
				var iwidget = this.getWidget('network', ikey);
				iwidget.set('value', lang.replace(ivalue, [subnet]));
			}, this);
		},

		_updateCitrixReceiverUploadPage: function() {
			if (this._info.citrix_receiver_deb_package) {
				var fileExistsMessage = _('<p>The following Citrix Receiver package file has already been uploaded: <i>%(file)s</i>.</p><p>It is possible to overwrite the existing package file and <a href="javascript:void(0)" onclick="require(\'dijit/registry\').byId(\'%(id)s\').showCitrixReceiverUploadWidgets()">upload a new one</a>.</p>', {
					file: this._info.citrix_receiver_deb_package,
					id: this.id
				});
				var fileExistsWidget = this.getWidget('terminalServices-thinclient-citrix-upload', 'fileExists');
				fileExistsWidget.set('content', fileExistsMessage);
				fileExistsWidget.set('visible', true);
				this.showCitrixReceiverUploadWidgets(false);
				this._setCitrixReceiverUploaded(true);  // enable next button
			} else {
				this.showCitrixReceiverUploadWidgets(true);
			}
		},

		showCitrixReceiverUploadWidgets: function(visible) {
			if (visible === undefined) {
				// toggle visibility
				visible = !this.getWidget('terminalServices-thinclient-citrix-upload', 'upload').get('visible');
			}
			array.forEach(['help', 'upload', 'eula'], function(ikey) {
				var widget = this.getWidget('terminalServices-thinclient-citrix-upload', ikey);
				widget.set('visible', visible);
			}, this);
		},

		_updateConfirmationPage: function() {
			var vals = this.getValues();
			var msg = '';
			if (vals.fatclient) {
				msg += '<p><b>' + _('Support for Linux desktop systems') + '</b></p>';
				if (vals.downloadFatClientImage) {
					msg += '<ul style="margin-top:0;"><li>' + _('Download of UCC desktop image [%.1f GB]', this._info.download_size_desktop / Math.pow(10, 9)) + '</li></ul>';
				}
			}
			if (vals.thinclient) {
				msg += '<p><b>' + _('Support for thin clients') + '</b></p>';
				msg += '<ul style="margin-top:0;">';
				if (vals.downloadThinClientImage) {
					msg += '<li>' + _('Download of UCC thin client image [%.1f GB]', this._info.download_size_thinclient / Math.pow(10, 9)) + '</li>';
				}

				if (vals.rdp) {
					msg += '<li>' + _('RDP server: <i>%s</i>', vals.rdp.host) + '</li>';
				}
				if (vals.citrix) {
					msg += '<li>' + _('Citrix server: <i>%s</i>', vals.citrix.url) + '</li>';
				}
				if (vals.browser) {
					msg += '<li>' + _('Web site access: <i>%s</i>', vals.browser.url) + '</li>';
				}
				msg += '</ul>';
			}
			msg += '<p><b>' + _('Network configuration') + '</b></p>';
			msg += '<ul style="margin-top:0;">';
			if (vals.network.existingDN) {
				var existingNetworkWidget = this.getWidget('network', 'existingNetwork');
				var networkLabel = '';
				array.forEach(existingNetworkWidget.getAllItems(), function(ientry) {
					if (ientry.id == vals.network.existingDN) {
						networkLabel = ientry.label;
					}
				});
				msg += '<li>' + _('Client network object: <i>network %s</i>', networkLabel) + '</li>';
			}
			else {
				msg += '<li>' + _('New client network object: <i>network %s</i>', vals.network.address) + '</li>';
			}
			if (vals.gateway) {
				msg += '<li>' + _('Gateway: <i>%s</i>', vals.gateway) + '</li>';
			}
			msg += '</ul>';
			this.getWidget('confirm', 'summary').set('content', msg);
		},

		_isPageVisible: function(pageName) {
			// if the gateway is already configured for DHCP, do not show the page
			// for configuring the gateway
			if (pageName == 'gateway' && this._info.dhcp_routing_policy) {
				return false;
			}

			// do not display the download page if a UCC image has already been installed
			if (pageName == 'download-thinclient' && this._info.has_installed_ucc_thinclient) {
				return false;
			}
			if (pageName == 'download-fatclient' && this._info.has_installed_ucc_desktop) {
				return false;
			}

			// general check
			return this._isPageForClientType(pageName) && this._isPageForTerminalServiceType(pageName);
		},

		_updateErrorPage: function(message) {
			message = message || _('An unexpected error occurred. More information about the cause of the error can be found in the log file /var/log/univention/management-console-module-uccsetup.log. Please retry to configure UCC after resolving any conflicting issues.');
			message = message.replace(/\n/g, '<br>');
			this.getWidget('error', 'info').set('content', message);
		},

		_applyConfiguration: function() {
			this.standby(false);
			this._progressBar.reset(_('Applying UCC configuration settings'));
			var vals = this.getValues();
			var deferred = tools.umcpProgressCommand(this._progressBar, 'uccsetup/apply', vals).then(lang.hitch(this, function(result) {
				this.standby(false);
				if (!result.success) {
					this._updateErrorPage(result.error);
					return 'error';
				}
				return 'done';
			}), lang.hitch(this, function(error) {
				// an alert dialogue with the traceback is shown automatically
				this.standby(false);
				this._updateErrorPage();
				return 'error';
			}));
			this.standbyDuring(deferred, this._progressBar);
			return deferred;
		},

		_ready: function() {
			var deferreds = array.map(this.pages, function(ipageConf) {
				var ipage = this.getPage(ipageConf.name);
				if (ipage._form) {
					return ipage._form.ready();
				}
				return null;
			}, this);
			deferreds.unshift(this._infoDeferred);
			return all(deferreds);
		},

		next: function(pageName) {
			var _inheritedNext = lang.hitch(this, this.inherited, arguments);
			var nextPage = _inheritedNext();
			while (!this._isPageVisible(nextPage)) {
				nextPage = _inheritedNext([nextPage]);
			}
			if (nextPage == 'confirm') {
				this._updateConfirmationPage();
			}
			if (pageName == 'download-thinclient') {
				this._updateDownloadThinClient();
			}
			if (pageName == 'confirm') {
				return this._applyConfiguration();
			}
			if (pageName == 'error') {
				return 'start';
			}
			var eulaWidget = this.getWidget('terminalServices-thinclient-citrix-upload', 'eula');
			var eulaAccepted = eulaWidget.get('value');
			var imageWidget = this.getWidget('terminalServices-thinclient-citrix-upload', 'image');
			if (pageName == 'terminalServices-thinclient-citrix-upload') {
				if (eulaWidget.get('visible') && !eulaAccepted) {
					dialog.alert(_('Please confirm the End User License Agreement of Citrix Receiver to proceed.'));
					return pageName;
				}
				if (!imageWidget.get('value')) {
					dialog.alert(_('Please specify a UCC image into which Citrix Receiver will be integrated.'));
					return pageName;
				}
			}
			var isAtLeastOneServiceSelected = this._getTerminalServices().length > 0;
			if (pageName == 'terminalServices-thinclient' && !isAtLeastOneServiceSelected) {
				dialog.alert(_('At least one terminal service needs to be configured.'));
				return pageName;
			}
			var isAtLeastOneClientTypeSelected = this._getClientType().length > 0;
			if (pageName == 'start' && !isAtLeastOneClientTypeSelected) {
				dialog.alert(_('At least one configuration type needs to be selected.'));
				return pageName;
			}
			return nextPage;
		},

		previous: function(pageName) {
			var _inheritedNext = lang.hitch(this, this.inherited, arguments);
			var previousPage = _inheritedNext();
			while (!this._isPageVisible(previousPage)) {
				previousPage = _inheritedNext([previousPage]);
			}
			return previousPage;
		},

		hasPrevious: function(pageName) {
			if (pageName == 'error' || pageName == 'done') {
				return false;
			}
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
		},

		startup: function() {
			this.inherited(arguments);
			this.wizard.startup();
		}
	});
});
