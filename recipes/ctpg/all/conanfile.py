from conans.errors import ConanInvalidConfiguration
from conans import ConanFile, tools
import os

required_conan_version = ">=1.33.0"

class CTPGConan(ConanFile):
    name = "ctpg"
    license = "MIT"
    description = (
        "Compile Time Parser Generator is a C++ single header library which takes a language description as a C++ code "
        "and turns it into a LR1 table parser with a deterministic finite automaton lexical analyzer, all in compile time."
    )
    topics = ("regex", "parser", "grammar", "compile-time")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/peter-winter/ctpg"
    settings = "compiler",
    no_copy_source = True

    _compiler_required_cpp17 = {
        "Visual Studio": "16",
        "gcc": "8",
        "clang": "12",
        "apple-clang": "12.0",
    }

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def validate(self):
        ## TODO: In ctpg<=1.3.5, Visual Studio C++ failed to compile ctpg with "error MSB6006: "CL.exe" exited with code -1073741571."
        if self.settings.compiler == "Visual Studio":
            raise ConanInvalidConfiguration(
                f"{self.name} does not support Visual Studio currently."
            )

        if self.settings.get_safe("compiler.cppstd"):
            tools.check_min_cppstd(self, "17")

        if minimum_version := self._compiler_required_cpp17.get(
            str(self.settings.compiler), False
        ):
            if tools.Version(self.settings.compiler.version) < minimum_version:
                raise ConanInvalidConfiguration(
                    f"{self.name} requires C++17, which your compiler does not support."
                )
        else:
            self.output.warn(
                f"{self.name} requires C++17. Your compiler is unknown. Assuming it supports C++17."
            )

    def package_id(self):
        self.info.header_only()

    def source(self):
        tools.get(**self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True)

    def package(self):
        self.copy("LICENSE*", "licenses", self._source_subfolder)
        if tools.Version(self.version) >= "1.3.7":
            self.copy("ctpg.hpp",
                os.path.join("include", "ctpg"), 
                os.path.join(self._source_subfolder, "include", "ctpg"))
        else:
            self.copy("ctpg.hpp", "include", os.path.join(self._source_subfolder, "include"))
