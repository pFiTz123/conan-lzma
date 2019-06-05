#!/usr/bin/env python
# -*- coding: utf-8 -*-
from conans import ConanFile, tools, AutoToolsBuildEnvironment, MSBuild
import os


class LZMAConan(ConanFile):
    name = "lzma"
    version = "5.2.4"
    description = "LZMA library is part of XZ Utils (a free general-purpose data compression software.)"
    url = "https://github.com/bincrafters/conan-lzma"
    homepage = "https://tukaani.org"
    license = "Public Domain"
    author = "Bincrafters <bincrafters@gmail.com>"
    exports = ["LICENSE.md"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {'shared': False, 'fPIC': True}
    _source_subfolder = 'sources'

    @property
    def _is_mingw_windows(self):
        # Linux MinGW doesn't require MSYS2 bash obviously
        return self.settings.compiler == 'gcc' and self.settings.os == 'Windows' and os.name == 'nt'

    @property
    def _msvc_version(self):
        switcher = {
            13: "vs2013",
            14: "vs2015",
            15: "vs2017",
            16: "vs2019"
        }
        version = int(self.settings.compiler.version.value)
        return switcher.get(version, "Invalid compiler version")

    @property
    def _msvc_buildtype(self):
        # treat 'RelWithDebInfo' and 'MinSizeRel' as 'Release'
        return 'Debug' if self.settings.build_type == 'Debug' else 'Release'

    def build_requirements(self):
        if self._is_mingw_windows:
            self.build_requires("msys2_installer/latest@bincrafters/stable")

    def configure(self):
        del self.settings.compiler.libcxx
        if self.settings.compiler == 'Visual Studio':
            del self.options.fPIC

    def source(self):
        git = tools.Git(folder=self._source_subfolder)
        git.clone("https://git.tukaani.org/xz.git", "master")

    def _build_msvc(self):
        with tools.chdir(os.path.join(self._source_subfolder, 'windows', self._msvc_version)):
            target = 'liblzma_dll' if self.options.shared else 'liblzma'
            msbuild = MSBuild(self)
            msbuild.build(
                'xz_win.sln',
                targets=[target],
                build_type=self._msvc_buildtype,
                platforms={'x86': 'Win32', 'x86_64': 'x64'},
                use_env=False)

    def _build_configure(self):
        with tools.chdir(self._source_subfolder):
            env_build = AutoToolsBuildEnvironment(self, win_bash=self._is_mingw_windows)
            args = ['--disable-xz',
                    '--disable-xzdec',
                    '--disable-lzmadec',
                    '--disable-lzmainfo',
                    '--disable-scripts',
                    '--disable-doc']
            if self.settings.os != "Windows" and self.options.fPIC:
                args.append('--with-pic')
            if self.options.shared:
                args.extend(['--disable-static', '--enable-shared'])
            else:
                args.extend(['--enable-static', '--disable-shared'])
            if self.settings.build_type == 'Debug':
                args.append('--enable-debug')
            env_build.configure(args=args, build=False)
            env_build.make()
            env_build.install()

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            self._build_msvc()
        else:
            self._build_configure()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        if self.settings.compiler == "Visual Studio":
            inc_dir = os.path.join(self._source_subfolder, 'src', 'liblzma', 'api')
            self.copy(pattern="*.h", dst="include", src=inc_dir, keep_path=True)
            arch = {'x86': 'Win32', 'x86_64': 'x64'}.get(str(self.settings.arch))
            target = 'liblzma_dll' if self.options.shared else 'liblzma'
            bin_dir = os.path.join(self._source_subfolder, 'windows', self._msvc_version,
                                   str(self._msvc_buildtype), arch, target)
            self.copy(pattern="*.lib", dst="lib", src=bin_dir, keep_path=False)
            if self.options.shared:
                self.copy(pattern="*.dll", dst="bin", src=bin_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.builddirs = ["lib/pkgconfig"]
        if not self.options.shared:
            self.cpp_info.defines.append('LZMA_API_STATIC')
        self.cpp_info.libs = tools.collect_libs(self)
