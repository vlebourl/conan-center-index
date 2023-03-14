from conans import ConanFile, AutoToolsBuildEnvironment, tools
from conans.errors import ConanInvalidConfiguration
import os
import glob

required_conan_version = ">=1.33.0"

class ElfutilsConan(ConanFile):
    name = "elfutils"
    description = "A dwarf, dwfl and dwelf functions to read DWARF, find separate debuginfo, symbols and inspect process state."
    homepage = "https://sourceware.org/elfutils"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("elfutils", "libelf", "libdw", "libasm")
    license = ["GPL-1.0-or-later", "LGPL-3.0-or-later", "GPL-2.0-or-later"]
    
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "debuginfod": [True, False],
        "libdebuginfod": [True, False],
        "with_bzlib": [True, False],
        "with_lzma": [True, False],
        "with_sqlite3": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "debuginfod": False,
        "libdebuginfod": False,
        "with_bzlib": True,
        "with_lzma": True,
        "with_sqlite3": False,
    }

    generators = "pkg_config"

    _autotools = None
    _source_subfolder = "source_subfolder"

    def export_sources(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            self.copy(patch["patch_file"])

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC
        if tools.Version(self.version) < "0.186":
            del self.options.libdebuginfod

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def validate(self):
        if tools.Version(self.version) >= "0.186":
            if self.settings.compiler in ["Visual Studio", "apple-clang", "msvc"]:
                raise ConanInvalidConfiguration("Compiler %s not supported. "
                            "elfutils only supports gcc and clang" % self.settings.compiler)
        elif self.settings.compiler in ["Visual Studio", "clang", "apple-clang", "msvc"]:
            raise ConanInvalidConfiguration("Compiler %s not supported. "
                        "elfutils only supports gcc" % self.settings.compiler)
        if self.settings.compiler != "gcc":
            self.output.warn(f"Compiler {self.settings.compiler} is not gcc.")

    def requirements(self):
        self.requires("zlib/1.2.12")
        if self.options.with_sqlite3:
            self.requires("sqlite3/3.38.5")
        if self.options.with_bzlib:
            self.requires("bzip2/1.0.8")
        if self.options.with_lzma:
            self.requires("xz_utils/5.2.5")
        if self.options.get_safe("libdebuginfod"):
            self.requires("libcurl/7.83.0")
        if self.options.debuginfod:
            # FIXME: missing recipe for libmicrohttpd
            raise ConanInvalidConfiguration("libmicrohttpd is not available (yet) on CCI")

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def build_requirements(self):
        self.build_requires("automake/1.16.4")
        self.build_requires("m4/1.4.19")
        self.build_requires("flex/2.6.4")
        self.build_requires("bison/3.7.6")
        self.build_requires("pkgconf/1.7.4")
        if self._settings_build.os == "Windows" and not tools.get_env("CONAN_BASH_PATH"):
            self.build_requires("msys2/cci.latest")
    
    def source(self):
        tools.get(**self.conan_data["sources"][self.version],
                  strip_root=True, destination=self._source_subfolder)

    def _configure_autotools(self):
        if not self._autotools:
            args = [
                "--disable-werror",
                f'--enable-static={"no" if self.options.shared else "yes"}',
                "--enable-deterministic-archives",
                "--enable-silent-rules",
                "--with-zlib",
                "--with-bzlib" if self.options.with_bzlib else "--without-bzlib",
                "--with-lzma" if self.options.with_lzma else "--without-lzma",
                "--enable-debuginfod"
                if self.options.debuginfod
                else "--disable-debuginfod",
            ]
            if tools.Version(self.version) >= "0.186":
                args.append("--enable-libdebuginfod" if self.options.libdebuginfod else "--disable-libdebuginfod")
            args.append(f'BUILD_STATIC={"0" if self.options.shared else "1"}')

            self._autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
            self._autotools.configure(configure_dir=self._source_subfolder, args=args)
        return self._autotools

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        with tools.chdir(self._source_subfolder):
            self.run("autoreconf -fiv")
        autotools = self._configure_autotools()
        autotools.make()
    
    def package(self):
        self.copy(pattern="COPYING*", dst="licenses", src=self._source_subfolder)
        autotools = self._configure_autotools()
        autotools.install()
        tools.rmdir(os.path.join(self.package_folder, "etc"))
        tools.rmdir(os.path.join(self.package_folder, "share"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        if self.options.shared:
            tools.remove_files_by_mask(os.path.join(self.package_folder, "lib"), "*.a")
        else:
            tools.remove_files_by_mask(os.path.join(self.package_folder, "lib"), "*.so")
            tools.remove_files_by_mask(os.path.join(self.package_folder, "lib"), "*.so.1")
        
    def package_info(self):
        # library components
        self.cpp_info.components["libelf"].libs = ["elf"]
        self.cpp_info.components["libelf"].requires = ["zlib::zlib"]

        self.cpp_info.components["libdw"].libs = ["dw"]
        self.cpp_info.components["libdw"].requires = ["libelf", "zlib::zlib"]
        if self.options.with_bzlib:
            self.cpp_info.components["libdw"].requires.append("bzip2::bzip2")
        if self.options.with_lzma:
            self.cpp_info.components["libdw"].requires.append("xz_utils::xz_utils")

        self.cpp_info.components["libasm"].includedirs = ["include/elfutils"]
        self.cpp_info.components["libasm"].libs = ["asm"]
        self.cpp_info.components["libasm"].requires = ["libelf", "libdw"]

        if self.options.get_safe("libdebuginfod"):
            self.cpp_info.components["libdebuginfod"].libs = ["debuginfod"]
            self.cpp_info.components["libdebuginfod"].requires = ["libcurl::curl"]

        # utilities
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH env var with : {bin_path}")
        self.env_info.PATH.append(bin_path)

        bin_ext = ".exe" if self.settings.os == "Windows" else ""

        addr2line = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-addr2line{bin_ext}")
        )
        self.output.info(f"Setting ADDR2LINE to {addr2line}")
        self.env_info.ADDR2LINE = addr2line

        ar = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-ar{bin_ext}")
        )
        self.output.info(f"Setting AR to {ar}")
        self.env_info.AR = ar

        elfclassify = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-elfclassify{bin_ext}")
        )
        self.output.info(f"Setting ELFCLASSIFY to {elfclassify}")
        self.env_info.ELFCLASSIFY = elfclassify

        elfcmp = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-elfcmp{bin_ext}")
        )
        self.output.info(f"Setting ELFCMP to {elfcmp}")
        self.env_info.ELFCMP = elfcmp

        elfcompress = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-elfcompress{bin_ext}")
        )
        self.output.info(f"Setting ELFCOMPRESS to {elfcompress}")
        self.env_info.ELFCOMPRESS = elfcompress

        elflint = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-elflint{bin_ext}")
        )
        self.output.info(f"Setting ELFLINT to {elflint}")
        self.env_info.ELFLINT = elflint

        findtextrel = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-findtextrel{bin_ext}")
        )
        self.output.info(f"Setting FINDTEXTREL to {findtextrel}")
        self.env_info.FINDTEXTREL = findtextrel

        make_debug_archive = tools.unix_path(
            os.path.join(
                self.package_folder, "bin", f"eu-make-debug-archive{bin_ext}"
            )
        )
        self.output.info(f"Setting MAKE_DEBUG_ARCHIVE to {make_debug_archive}")
        self.env_info.MAKE_DEBUG_ARCHIVE = make_debug_archive

        nm = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-nm{bin_ext}")
        )
        self.output.info(f"Setting NM to {nm}")
        self.env_info.NM = nm

        objdump = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-objdump{bin_ext}")
        )
        self.output.info(f"Setting OBJDUMP to {objdump}")
        self.env_info.OBJDUMP = objdump

        ranlib = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-ranlib{bin_ext}")
        )
        self.output.info(f"Setting RANLIB to {ranlib}")
        self.env_info.RANLIB = ranlib

        readelf = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-readelf{bin_ext}")
        )
        self.output.info(f"Setting READELF to {readelf}")
        self.env_info.READELF = readelf

        size = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-size{bin_ext}")
        )
        self.output.info(f"Setting SIZE to {size}")
        self.env_info.SIZE = size

        stack = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-stack{bin_ext}")
        )
        self.output.info(f"Setting STACK to {stack}")
        self.env_info.STACK = stack

        strings = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-strings{bin_ext}")
        )
        self.output.info(f"Setting STRINGS to {strings}")
        self.env_info.STRINGS = strings

        strip = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-strip{bin_ext}")
        )
        self.output.info(f"Setting STRIP to {strip}")
        self.env_info.STRIP = strip

        unstrip = tools.unix_path(
            os.path.join(self.package_folder, "bin", f"eu-unstrip{bin_ext}")
        )
        self.output.info(f"Setting UNSTRIP to {unstrip}")
        self.env_info.UNSTRIP = unstrip

