#!/usr/bin/python

## Binary Analysis Tool
## Copyright 2009-2013 Armijn Hemel for Tjaldur Software Governance Solutions
## Licensed under Apache 2.0, see LICENSE file for details

'''
This file contains a few methods that check for the presence of marker
strings that are likely to be found in certain programs. It is far from fool
proof and false positives are likely, so either check the results, or replace
it with your own more robust checks.
'''

import string, re, os, magic, subprocess, sys, tempfile, copy
import extractor
import xml.dom.minidom

## generic searcher for certain marker strings
def genericSearch(path, markerStrings, blacklist=[]):
        try:
		## first see if the entire file has been blacklisted
		filesize = os.stat(path).st_size
		carved = False
		if blacklist != []:
			if extractor.inblacklist(0, blacklist) == filesize:
				return None
			datafile = open(path, 'rb')
			lastindex = 0
			databytes = ""
			datafile.seek(lastindex)
			## make a copy and add a bogus value for the last
			## byte to a temporary blacklist to make the loop work
			## well.
			blacklist_tmp = copy.deepcopy(blacklist)
			blacklist_tmp.append((filesize,filesize))
			for i in blacklist_tmp:
				if i[0] == lastindex:
					lastindex = i[1] - 1
					datafile.seek(lastindex)
					continue
				if i[0] > lastindex:
					## just concatenate the bytes
					data = datafile.read(i[0] - lastindex)
					databytes = databytes + data
					## set lastindex to the next
					lastindex = i[1] - 1
					datafile.seek(lastindex)
			datafile.close()
			if len(databytes) == 0:
				return None
			tmpfile = tempfile.mkstemp()
			os.write(tmpfile[0], databytes)
			os.fdopen(tmpfile[0]).close()
			scanfile = tmpfile[1]
			carved = True
			path = tmpfile[1]

		datafile = open(path, 'rb')
		databuffer = []
		offset = 0
		datafile.seek(offset)
		databuffer = datafile.read(100000)
		while databuffer != '':
			for marker in markerStrings:
				markeroffset = databuffer.find(marker)
				if markeroffset != -1:
					if carved:
						os.unlink(path)
					return True
			## move the offset 100000
			datafile.seek(offset + 100000)
			databuffer = datafile.read(100000)
			offset = offset + len(databuffer)
		datafile.close()
		if carved:
			os.unlink(path)
        except Exception, e:
                return None
	return None

## The result of this method is a list of library names that the file dynamically links
## with. The path of these libraries is not given, since this is usually not recorded
## in the binary (unless RPATH is used) but determined at runtime: it is dependent on
## the dynamic linker configuration on the device. With some mixing and matching it is
## nearly always to determine which library in which path is used, since most installations
## don't change the default search paths.
def searchDynamicLibs(path, blacklist=[], envvars=None):
	ms = magic.open(magic.MAGIC_NONE)
	ms.load()
	mstype = ms.file(path)
	ms.close()
	if "ELF" in mstype:
		libs = []
		p = subprocess.Popen(['readelf', '-d', "%s" % (path,)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
		(stanout, stanerr) = p.communicate()
		if p.returncode != 0:
                	return
		for line in stanout.split('\n'):
			if "Shared library:" in line:
				libs.append(line.split(': ')[1][1:-1])
		if libs == []:
			return None
		else:
			return (['libs'], libs)

def dynamicLibsPrettyPrint(res, root, envvars=None):
	tmpnode = root.createElement('libs')
	for lib in res:
		tmpnode2 = root.createElement('lib')
		tmpnodetext = xml.dom.minidom.Text()
		tmpnodetext.data = lib
		tmpnode2.appendChild(tmpnodetext)
		tmpnode.appendChild(tmpnode2)
	return tmpnode

## This method uses readelf to determine the architecture of the executable file.
## This is necessary because sometimes leftovers from different products (and
## different architectures) can be found in one firmware.
def scanArchitecture(path, blacklist=[], envvars=None):
	ms = magic.open(magic.MAGIC_NONE)
	ms.load()
	mstype = ms.file(path)
	ms.close()
	if "ELF" in mstype:
		p = subprocess.Popen(['readelf', '-h', "%s" % (path,)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
		(stanout, stanerr) = p.communicate()
		if p.returncode != 0:
			return
		for line in stanout.split('\n'):
			if "Machine:" in line:
				return (['architecture'], line.split(':')[1].strip())

def searchLoadLin(path, blacklist=[], envvars=None):
	markerStrings = [ 'Ooops..., size of "setup.S" has become too long for LOADLIN,'
			, 'LOADLIN started from $'
			]
	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['loadlin'], res)

def searchIptables(path, blacklist=[], envvars=None):
	markerStrings = [ 'iptables who? (do you need to insmod?)'
			, 'Will be implemented real soon.  I promise ;)'
			, 'can\'t initialize iptables table `%s\': %s'
			]
	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['iptables'], res)

def searchDproxy(path, blacklist=[], envvars=None):
	markerStrings = [ '# dproxy monitors this file to determine when the machine is'
			, '# If you want dproxy to log debug info specify a file here.'
			]
	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['dproxy'], res)

def searchEzIpupdate(path, blacklist=[], envvars=None):
	markerStrings = [ 'ez-ipupdate Version %s, Copyright (C) 1998-'
			, '%s says that your IP address has not changed since the last update'
			, 'you must provide either an interface or an address'
			]
	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['ez-ipupdate'], res)

def searchLibusb(path, blacklist=[], envvars=None):
	markerStrings = [ 'Check that you have permissions to write to %s/%s and, if you don\'t, that you set up hotplug (http://linux-hotplug.sourceforge.net/) correctly.'
			, 'usb_os_find_busses: Skipping non bus directory %s'
			, 'usb_os_init: couldn\'t find USB VFS in USB_DEVFS_PATH'
			]
	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['libusb'], res)

def searchVsftpd(path, blacklist=[], envvars=None):
	markerStrings = [ 'vsftpd: version'
			, '(vsFTPd '
			, 'VSFTPD_LOAD_CONF'
			, 'run two copies of vsftpd for IPv4 and IPv6'
			]

	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['vsftpd'], res)

def searchHostapd(path, blacklist=[], envvars=None):
	markerStrings = [ 'hostapd v'
			]

	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['hostapd'], res)

def searchWpaSupplicant(path, blacklist=[], envvars=None):
	markerStrings = [ 'wpa_supplicant v'
			]

	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['wpasupplicant'], res)

def searchIproute(path, blacklist=[], envvars=None):
	markerStrings = [ 'Usage: tc [ OPTIONS ] OBJECT { COMMAND | help }'
			, 'tc utility, iproute2-ss%s'
			, 'Option "%s" is unknown, try "tc -help".'
			]

	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['iproute2'], res)

def searchWirelessTools(path, blacklist=[], envvars=None):
	markerStrings = [ "Driver has no Wireless Extension version information."
			, "Wireless Extension version too old."
			, "Wireless-Tools version"
			, "Wireless Extension, while we are using version %d."
			, "Currently compiled with Wireless Extension v%d."
       	                ]

	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['wireless-tools'], res)

def searchRedBoot(path, blacklist=[], envvars=None):
	markerStrings = ["Display RedBoot version information"]

	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['redboot'], res)

def searchUBoot(path, blacklist=[], envvars=None):
        markerStrings = [ "run script starting at addr"
			, "Hit any key to stop autoboot: %2d"
			, "## Binary (kermit) download aborted"
			, "## Ready for binary (ymodem) download "
			]

	res = genericSearch(path, markerStrings, blacklist)
	if res != None:
		return (['uboot'], res)

## What actually do these dependencies mean?
## Are they dependencies of the installer itself, or of the programs that are
## installed by the installer?
def searchWindowsDependencies(path, blacklist=[], envvars=None):
	## first determine if we are dealing with a MS Windows executable
	ms = magic.open(magic.MAGIC_NONE)
	ms.load()
	mstype = ms.file(path)
	ms.close()
	if not 'PE32 executable for MS Windows' in mstype and not "PE32+ executable for MS Windows" in mstype:
                return None
        binary = open(path, 'rb')
        lines = binary.read()
	binary.close()
	deps = extractor.searchAssemblyDeps(lines)
	if deps == None:
		return None
	if deps == []:
		return None
	else:
		return (['windowsdependencies'], deps)

def xmlPrettyPrintWindowsDeps(res, root, envvars=None):
	pass

## method to extract meta information from PDF files
def scanPDF(path, blacklist=[], envvars=None):
	## we only want to scan whole PDF files. If anything has been carved from
	## it, we don't want to see it. Blacklists are a good indicator, but we
	## should have some way to prevent other scans from analysing this file.
	if blacklist != []:
		return None
	ms = magic.open(magic.MAGIC_NONE)
	ms.load()
	mstype = ms.file(path)
	ms.close()
	if not 'PDF document' in mstype:
                return None
	else:
		p = subprocess.Popen(['pdfinfo', "%s" % (path,)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
		(stanout, stanerr) = p.communicate()
		if p.returncode != 0:
                	return
		else:
			pdfinfo = {}
			pdflines = stanout.rstrip().split("\n")
			for pdfline in pdflines:
				(tag, value) = pdfline.split(":", 1)
				if tag == "Title":
					pdfinfo['title'] = value.strip()
				if tag == "Author":
					pdfinfo['author'] = value.strip()
				if tag == "Creator":
					pdfinfo['creator'] = value.strip()
				if tag == "CreationDate":
					pdfinfo['creationdate'] = value.strip()
				if tag == "Producer":
					pdfinfo['producer'] = value.strip()
				if tag == "Tagged":
					pdfinfo['tagged'] = value.strip()
				if tag == "Pages":
					pdfinfo['pages'] = int(value.strip())
				if tag == "Page size":
					pdfinfo['pagesize'] = value.strip()
				if tag == "Encrypted":
					pdfinfo['encrypted'] = value.strip()
				if tag == "Optimized":
					pdfinfo['optimized'] = value.strip()
				if tag == "PDF version":
					pdfinfo['version'] = value.strip()
			return (['pdfinfo'], pdfinfo)

def pdfPrettyPrint(res, root, envvars=None):
	tmpnode = root.createElement('pdfinfo')
	for key in res:
		tmpnode2 = root.createElement(key)
		tmpnodetext = xml.dom.minidom.Text()
		tmpnodetext.data = str(res[key])
		tmpnode2.appendChild(tmpnodetext)
		tmpnode.appendChild(tmpnode2)
	return tmpnode

## scan for mentions of:
## * GPL
## * Apache
######################################
## !!! WARNING WARNING WARNING !!! ###
######################################
## This should only be used as an indicator for further investigation,
## never as proof that a binary is actually licensed under a license!
def scanLicenses(path, blacklist=[], envvars=None):
	results = {}
	if genericSearch(path, ["General Public License", "http://www.gnu.org/licenses/", "http://gnu.org/licenses/", "http://www.gnu.org/gethelp/", "http://www.gnu.org/software/"], blacklist):
		results['GNU'] = True
	if genericSearch(path, ["http://gnu.org/licenses/gpl.html", "http://www.gnu.org/licenses/gpl.html",
                                "http://www.opensource.org/licenses/gpl-license.php", "http://www.gnu.org/copyleft/gpl.html"], blacklist):
		results['GPL'] = True
	if genericSearch(path, ["http://gnu.org/licenses/gpl-2.0.html", "http://www.gnu.org/licenses/old-licenses/gpl-2.0.html"], blacklist):
		results['GPLv2'] = True
	if genericSearch(path, ["http://gnu.org/licenses/old-licenses/lgpl-2.1.html"], blacklist):
		results['LGPLv2.1'] = True
	if genericSearch(path, ["http://www.apache.org/licenses/LICENSE-2.0", "http://opensource.org/licenses/apache2.0.php"], blacklist):
		results['Apache2.0'] = True
	if genericSearch(path, ["http://www.mozilla.org/MPL/"], blacklist):
		results['MPL'] = True
	if genericSearch(path, ["http://www.opensource.org/licenses/mit-license.php"], blacklist):
		results['MIT'] = True
	if genericSearch(path, ["http://www.opensource.org/licenses/bsd-license.php"], blacklist):
		results['BSD'] = True
	if genericSearch(path, ["http://www.openoffice.org/license.html"], blacklist):
		results['OpenOffice'] = True
	if genericSearch(path, ["http://www.bittorrent.com/license/"], blacklist):
		results['BitTorrent'] = True
	if genericSearch(path, ["http://www.tizenopensource.org/license"], blacklist):
		results['Tizen'] = True
	if results != {}:
		return (['licenses'], results)
	else:
		return None

def licensesPrettyPrint(res, root, envvars=None):
	tmpnode = root.createElement('licenses')
	for key in res:
		tmpnode2 = root.createElement(key)
		tmpnode.appendChild(tmpnode2)
	return tmpnode

## scan for mentions of several forges
## Some of the URLs of the forges no longer work or are redirected, but they
## might still pop up in binaries.
def scanForges(path, blacklist=[], envvars=None):
	results = {}
	if genericSearch(path, ["sourceforge.net"], blacklist):
		results['sourceforge.net'] = True
	if genericSearch(path, ["http://cvs.freedesktop.org/", "http://cgit.freedesktop.org/"], blacklist):
		results['freedesktop.org'] = True
	if genericSearch(path, ["code.google.com", "googlecode.com"], blacklist):
		results['code.google.com'] = True
	if genericSearch(path, ["savannah.gnu.org/"], blacklist):
		results['savannah.gnu.org'] = True
	if genericSearch(path, ["github.com"], blacklist):
		results['github.com'] = True
	if genericSearch(path, ["bitbucket.org"], blacklist):
		results['bitbucket.org'] = True
	if genericSearch(path, ["tigris.org"], blacklist):
		results['tigris.org'] = True
	if genericSearch(path, ["http://svn.apache.org/"], blacklist):
		results['svn.apache.org'] = True
	## various gits:
	## http://git.fedoraproject.org/git/
	## https://fedorahosted.org/
	if results != {}:
		return (['forges'], results)
	else:
		return None

def forgesPrettyPrint(res, root, envvars=None):
	tmpnode = root.createElement('forges')
	for key in res:
		tmpnode2 = root.createElement(key)
		tmpnode.appendChild(tmpnode2)
	return tmpnode

## experimental clamscan feature
## Always run freshclam before scanning to get the latest
## virus signatures!
def scanVirus(path, blacklist=[], envvars=None):
	p = subprocess.Popen(['clamscan', "%s" % (path,)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
	(stanout, stanerr) = p.communicate()
	if p.returncode == 0:
               	return
	else:
		## Oooh, virus found!
		viruslines = stanout.split("\n")
		## first line contains the report:
		virusname = viruslines[0].strip()[len(path) + 2:-6]
		return (['virus'], virusname)
