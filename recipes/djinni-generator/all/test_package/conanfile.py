
from io import StringIO
from conans import ConanFile, tools

class TestPackageConan(ConanFile):
    settings = "os", "arch"

    def build(self):
        pass # please no warning that we build nothing

    def test(self):
        if tools.cross_building(self.settings):
            return
        output = StringIO()
        self.run("djinni --help", output=output, run_environment=True)
        output.seek(0, 0)
        found_usage = any("Usage: djinni [options]" in line for line in output)
        assert(found_usage)
