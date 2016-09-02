#!/usr/bin/env python
#############################################################################
##
## Copyright (C) 2014 Digia Plc and/or its subsidiary(-ies).
## Contact: http://www.qt-project.org/legal
##
## This file is part of the release tools of the Qt Toolkit.
##
## $QT_BEGIN_LICENSE:LGPL$
## Commercial License Usage
## Licensees holding valid commercial Qt licenses may use this file in
## accordance with the commercial license agreement provided with the
## Software or, alternatively, in accordance with the terms contained in
## a written agreement between you and Digia.  For licensing terms and
## conditions see http://qt.digia.com/licensing.  For further information
## use the contact form at http://qt.digia.com/contact-us.
##
## GNU Lesser General Public License Usage
## Alternatively, this file may be used under the terms of the GNU Lesser
## General Public License version 2.1 as published by the Free Software
## Foundation and appearing in the file LICENSE.LGPL included in the
## packaging of this file.  Please review the following information to
## ensure the GNU Lesser General Public License version 2.1 requirements
## will be met: http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html.
##
## In addition, as a special exception, Digia gives you certain additional
## rights.  These rights are described in the Digia Qt LGPL Exception
## version 1.1, included in the file LGPL_EXCEPTION.txt in this package.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3.0 as published by the Free Software
## Foundation and appearing in the file LICENSE.GPL included in the
## packaging of this file.  Please review the following information to
## ensure the GNU General Public Lhttps://www.google.fi/icense version 3.0 requirements will be
## met: http://www.gnu.org/copyleft/gpl.html.
##
##
## $QT_END_LICENSE$
##
#############################################################################

import glob
import os
import subprocess

import bld_utils
import bldinstallercommon
import environmentfrombatchfile

def get_clang(base_path, branch):
    bld_utils.runCommand(['git', 'clone', '--branch', branch, 'http://llvm.org/git/llvm.git'], base_path)
    bld_utils.runCommand(['git', 'clone', '--branch', branch, 'http://llvm.org/git/clang.git'], os.path.join(base_path, 'llvm', 'tools'))

def apply_patch(src_path, patch_filepath):
    print('Applying patch: "' + patch_filepath + '" in "' + src_path + '"')
    with open(patch_filepath, 'r') as f:
        subprocess.check_call(['patch', '-p2'], stdin=f, cwd=src_path)

def apply_patches(src_path, patch_filepaths):
    for patch in patch_filepaths:
        apply_patch(src_path, patch)

def cmake_generator():
    return 'NMake Makefiles JOM' if bldinstallercommon.is_win_platform() else 'Unix Makefiles'

def bitness_flags(bitness):
    if bitness == 64:
        flags = ['-DLLVM_TARGETS_TO_BUILD=AArch64']
    else:
        flags = ['-DLLVM_TARGETS_TO_BUILD=X86']
        if bldinstallercommon.is_linux_platform():
            flags.extend(['-DLIBXML2_LIBRARIES=/usr/lib/libxml2.so', '-DLLVM_BUILD_32_BITS=ON'])
    return flags

def make_command():
    return ["jom"] if bldinstallercommon.is_win_platform() else ["make"]

def install_command():
    return ["nmake", "install"] if bldinstallercommon.is_win_platform() else ["make", "-j1", "install"]

def build_clang(src_path, build_path, install_path, bitness=64, environment=None, build_type='Release'):
    cmake_command = ['cmake',
                     '-DCMAKE_INSTALL_PREFIX=' + install_path,
                     '-G',
                     cmake_generator(),
                     '-DCMAKE_BUILD_TYPE=' + build_type]
    cmake_command.extend(bitness_flags(bitness))
    cmake_command.append(src_path)
    bld_utils.runCommand(cmake_command, build_path, init_environment=environment)
    bld_utils.runCommand(make_command(), build_path, init_environment=environment)
    bld_utils.runCommand(install_command(), build_path, init_environment=environment)

def package_clang(install_path, result_file_path):
    (basepath, dirname) = os.path.split(install_path)
    zip_command = ['7z', 'a', result_file_path, dirname]
    bld_utils.runCommand(zip_command, basepath)

def upload_clang(file_path, remote_path):
    (path, filename) = os.path.split(file_path)
    scp_bin = '%SCP%' if bldinstallercommon.is_win_platform() else 'scp'
    scp_command = [scp_bin, filename, remote_path]
    bld_utils.runCommand(scp_command, path)

def build_environment(bitness):
    if bldinstallercommon.is_win_platform():
        program_files = os.path.join('C:', '/Program Files (x86)')
        if not os.path.exists(program_files):
            program_files = os.path.join('C:', '/Program Files')
        vcvarsall = os.path.join(program_files, 'Microsoft Visual Studio ' + os.environ['MSVC_VERSION'], 'VC', 'vcvarsall.bat')
        arg = 'amd64' if bitness == 64 else 'x86'
        return environmentfrombatchfile.get(vcvarsall, arguments=arg)
    else:
        return None # == process environment

def main():
    bldinstallercommon.init_common_module(os.path.dirname(os.path.realpath(__file__)))
    base_path = os.path.join(os.environ['PKG_NODE_ROOT'], 'build')
    branch = os.environ['CLANG_BRANCH']
    src_path = os.path.join(base_path, 'llvm')
    clang_src_path = os.path.join(base_path, 'llvm', 'tools', 'clang')
    patch_src_path = os.path.join(base_path, 'tqtc-testconfig', 'projects', os.environ['PULSE_PROJECT'], 'stages', 'patches')
    build_path = os.path.join(base_path, 'build')
    install_path = os.path.join(base_path, 'libclang')
    bitness = 64 if '64' in os.environ['cfg'] else 32
    environment = build_environment(bitness)
    result_file_path = os.path.join(base_path, 'libclang-' + branch + '-' + os.environ['CLANG_PLATFORM'] + '.7z')
    remote_path = (os.environ['PACKAGE_STORAGE_SERVER_USER'] + '@' + os.environ['PACKAGE_STORAGE_SERVER'] + ':'
                   + os.environ['PACKAGE_STORAGE_SERVER_BASE_DIR'] + '/' + os.environ['CLANG_UPLOAD_SERVER_PATH'])
    get_clang(base_path, branch)
    apply_patches(clang_src_path, sorted(glob.glob(os.path.join(patch_src_path, '*'))))
    build_clang(src_path, build_path, install_path, bitness, environment, build_type='Release')
    package_clang(install_path, result_file_path)
    upload_clang(result_file_path, remote_path)

if __name__ == "__main__":
    main()