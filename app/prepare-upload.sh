#!/bin/bash

outdir="app_center_upload_dir"
src_host="omar"
package_source="${src_host}:/var/univention/buildsystem2/apt/"
base_version="ucs_4.1-0"
ucc_scope="-ucc-3.0-integration"

[ -e ${outdir} ] && rm -r ${outdir}
mkdir -p ${outdir}/packages/{all,i386,amd64,source}

# copy local files
cp *ini *svg *png README* ${outdir}

# copy files from integration scope
scp ${package_source}${base_version}${ucc_scope}/all/*deb ${outdir}/packages/all
scp ${package_source}${base_version}${ucc_scope}/i386/*deb ${outdir}/packages/i386
scp ${package_source}${base_version}${ucc_scope}/amd64/*deb ${outdir}/packages/amd64
scp ${package_source}${base_version}${ucc_scope}/source/{*dsc,*tar.gz,*changes} ${outdir}/packages/source

scp ${src_host}:/var/univention/buildsystem2/mirror/ftp/4.0/unmaintained/4.0-0/i386/python-lzma_0.5.3-2.4.201403130724_i386.deb ${outdir}/packages/i386
scp ${src_host}:/var/univention/buildsystem2/mirror/ftp/4.0/unmaintained/4.0-0/i386/python-lzma-dbg_0.5.3-2.4.201403130724_i386.deb ${outdir}/packages/i386
scp ${src_host}:/var/univention/buildsystem2/mirror/ftp/4.0/unmaintained/4.0-0/amd64/python-lzma_0.5.3-2.4.201403130724_amd64.deb ${outdir}/packages/amd64
scp ${src_host}:/var/univention/buildsystem2/mirror/ftp/4.0/unmaintained/4.0-0/amd64/python-lzma-dbg_0.5.3-2.4.201403130724_amd64.deb ${outdir}/packages/amd64

# build tar.gz for appcenter selfservice
cd $outdir
tar czvf ../ucc-3.0.tar.gz *
cd ..

[ ! "${1}" == "--no-delete" ] && rm -r ${outdir}
